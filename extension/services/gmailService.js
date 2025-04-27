// Gmail API service
class GmailService {
    constructor() {
        this.API_URL = 'https://gmail.googleapis.com/gmail/v1';
    }

    async getCurrentEmail() {
        try {
            // Get the current thread ID from the URL
            const threadId = this.getThreadIdFromUrl();
            if (!threadId) {
                console.error('No thread ID found in URL');
                return null;
            }

            // Get the thread details
            const thread = await this.getThread(threadId);
            if (!thread) {
                console.error('Failed to get thread');
                return null;
            }

            // Get the latest message (current email being composed)
            const latestMessage = thread.messages[thread.messages.length - 1];
            const message = await this.getMessage(latestMessage.id);
            
            // Get the previous messages for the chain
            const previousMessages = thread.messages.slice(0, -1).reverse();
            const emailChain = await Promise.all(
                previousMessages.map(msg => this.getMessage(msg.id))
            );

            return {
                subject: message.payload && message.payload.headers ? this.getHeader(message.payload.headers, 'Subject') : '',
                content: this.decodeMessageBody(message.payload),
                recipients: {
                    to: message.payload && message.payload.headers ? this.getHeader(message.payload.headers, 'To') : '',
                    cc: message.payload && message.payload.headers ? this.getHeader(message.payload.headers, 'Cc') : '',
                    bcc: message.payload && message.payload.headers ? this.getHeader(message.payload.headers, 'Bcc') : ''
                },
                emailChain: emailChain.map(msg => ({
                    from: msg.payload && msg.payload.headers ? this.getHeader(msg.payload.headers, 'From') : '',
                    content: this.decodeMessageBody(msg.payload)
                })),
                isReply: thread.messages.length > 1
            };
        } catch (error) {
            console.error('Error getting current email:', error);
            return null;
        }
    }

    getThreadIdFromUrl() {
        const match = window.location.href.match(/thread\/([a-zA-Z0-9-_]+)/);
        return match ? match[1] : null;
    }

    async getThread(threadId) {
        const response = await fetch(`${this.API_URL}/users/me/threads/${threadId}`, {
            headers: {
                'Authorization': `Bearer ${await this.getAccessToken()}`
            }
        });
        return response.ok ? await response.json() : null;
    }

    async getMessage(messageId) {
        const response = await fetch(`${this.API_URL}/users/me/messages/${messageId}`, {
            headers: {
                'Authorization': `Bearer ${await this.getAccessToken()}`
            }
        });
        return response.ok ? await response.json() : null;
    }

    getHeader(headers, name) {
        const header = headers.find(h => h.name.toLowerCase() === name.toLowerCase());
        return header ? header.value : '';
    }

    decodeMessageBody(payload) {
        if (payload.parts) {
            // Get the plain text part
            const textPart = payload.parts.find(part => part.mimeType === 'text/plain');
            if (textPart && textPart.body && textPart.body.data) {
                return atob(textPart.body.data.replace(/-/g, '+').replace(/_/g, '/'));
            }
        }
        if (payload.body && payload.body.data) {
            return atob(payload.body.data.replace(/-/g, '+').replace(/_/g, '/'));
        }
        return ''; // or null, or throw an error, depending on your needs
    }

    async getAccessToken() {
        return new Promise((resolve, reject) => {
            chrome.identity.getAuthToken({ interactive: true }, token => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(token);
                }
            });
        });
    }

    // Fetch the last N sent emails
    async getLastSentEmails(maxResults = 100) {
        const token = await this.getAccessToken();
        // Get the last N sent message IDs
        const listRes = await fetch(`${this.API_URL}/users/me/messages?labelIds=SENT&maxResults=${maxResults}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const listData = await listRes.json();
        if (!listData.messages) return [];
        
        // Track processed email IDs to prevent duplicates
        const processedIds = new Set();
        const uniqueMessages = [];
        
        // Only keep messages with unique IDs
        for (const msg of listData.messages) {
            if (!processedIds.has(msg.id)) {
                processedIds.add(msg.id);
                uniqueMessages.push(msg);
            }
        }
        
        console.log(`Found ${listData.messages.length} messages, ${uniqueMessages.length} are unique`);
        
        // Fetch each message's details
        const emails = await Promise.all(uniqueMessages.map(async (msg) => {
            try {
                const msgRes = await fetch(`${this.API_URL}/users/me/messages/${msg.id}?format=full`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const msgData = await msgRes.json();
                // Check for payload and headers existence
                const headers = msgData.payload && msgData.payload.headers ? msgData.payload.headers : [];
                const subject = this.getHeader(headers, 'Subject');
                const to = this.getHeader(headers, 'To');
                const from = this.getHeader(headers, 'From');
                const date = this.getHeader(headers, 'Date');
                const body = this.decodeMessageBody(msgData.payload || {});
                return { subject, to, from, date, body, id: msg.id };
            } catch (error) {
                console.error(`Error fetching message ${msg.id}:`, error);
                return null;
            }
        }));
        
        // Filter out any null results from failed fetches
        return emails.filter(email => email !== null);
    }
}

// Export the service
const gmailService = new GmailService();
export default gmailService; 