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
                subject: this.getHeader(message.payload.headers, 'Subject'),
                content: this.decodeMessageBody(message.payload),
                recipients: {
                    to: this.getHeader(message.payload.headers, 'To'),
                    cc: this.getHeader(message.payload.headers, 'Cc'),
                    bcc: this.getHeader(message.payload.headers, 'Bcc')
                },
                emailChain: emailChain.map(msg => ({
                    from: this.getHeader(msg.payload.headers, 'From'),
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
            if (textPart) {
                return atob(textPart.body.data.replace(/-/g, '+').replace(/_/g, '/'));
            }
        }
        return atob(payload.body.data.replace(/-/g, '+').replace(/_/g, '/'));
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
}

// Export the service
const gmailService = new GmailService();
export default gmailService; 