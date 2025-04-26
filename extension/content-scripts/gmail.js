// Initialize Gmail.js
let gmail;

function initializeGmail() {
    try {
        // Make sure jQuery is available
        if (typeof jQuery === 'undefined') {
            throw new Error('jQuery not loaded');
        }
        
        // Initialize Gmail with jQuery
        gmail = new Gmail($);
        console.log('Gmail.js initialized successfully');
        return true;
    } catch (error) {
        console.error('Failed to initialize Gmail.js:', error);
        return false;
    }
}

// Gmail selectors for reliable data extraction
const SELECTORS = {
    COMPOSE_BODY: '.Am.Al.editable[role="textbox"]',
    SUBJECT: 'input[name="subjectbox"]',
    RECIPIENTS: {
        TO: '[name="to"]',
        CC: '[name="cc"]',
        BCC: '[name="bcc"]'
    },
    RECIPIENT_CHIPS: {
        TO: '[role="presentation"] [email]',
        CC: '[name="cc"] + [role="presentation"] [email]',
        BCC: '[name="bcc"] + [role="presentation"] [email]'
    }
};

// Function to wait for an element to be present in the DOM
function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }

        const observer = new MutationObserver((mutations, obs) => {
            const element = document.querySelector(selector);
            if (element) {
                obs.disconnect();
                resolve(element);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Timeout waiting for element: ${selector}`));
        }, timeout);
    });
}

// Function to get user email from storage
function getUserEmailFromStorage() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['user'], function(result) {
            if (result.user && result.user.email) {
                resolve(result.user.email);
            } else {
                resolve('anonymous');
            }
        });
    });
}

// Function to get compose data
async function getComposeData() {
    console.log('Getting compose data');
    
    // Get the active compose element
    const composeElem = document.querySelector('.Am.Al.editable[role="textbox"]');
    if (!composeElem) {
        console.error('No compose element found');
        return null;
    }

    // Get subject
    const subjectElem = document.querySelector('input[name="subjectbox"]');
    const subject = subjectElem ? subjectElem.value : '';

    // Get content
    const content = composeElem.innerText || '';

    // Get recipients
    const recipients = {
        to: getRecipients('TO'),
        cc: getRecipients('CC'),
        bcc: getRecipients('BCC')
    };

    // Check if this is a reply
    const isReply = window.location.href.includes('?rm=r') || 
                   window.location.href.includes('?rm=f') ||
                   document.querySelector('.adn.ads') !== null;

    // Get email chain for replies
    let emailChain = '';
    if (isReply) {
        const threadContainer = document.querySelector('.adn.ads');
        if (threadContainer) {
            emailChain = threadContainer.innerText || '';
        }
    }

    // Get user email from storage
    const userEmail = await getUserEmailFromStorage();
    console.log('Got user email from storage:', userEmail);

    const data = {
        user_id: userEmail,
        subject: subject,
        content: content,
        recipients: recipients,
        email_chain: emailChain,
        is_reply: isReply,
        timestamp: new Date().toISOString()
    };

    console.log('Extracted data:', data);
    return data;
}

// Function to get recipients (both from input fields and chips)
function getRecipients(type) {
    const recipients = new Set();
    
    // Get from input field
    const input = document.querySelector(SELECTORS.RECIPIENTS[type]);
    if (input && input.value) {
        recipients.add(input.value);
    }
    
    // Get from chips
    const chips = document.querySelectorAll(SELECTORS.RECIPIENT_CHIPS[type]);
    chips.forEach(chip => {
        const email = chip.getAttribute('email');
        if (email) {
            recipients.add(email);
        }
    });
    
    return Array.from(recipients).join(', ');
}

// Function to get user email
function getUserEmail() {
    // Try getting from Gmail profile
    const profileElem = document.querySelector('.gb_d.gb_Na.gb_g');
    if (profileElem) {
        return profileElem.getAttribute('aria-label') || 'anonymous';
    }
    
    // Fallback to other selectors
    const emailElems = document.querySelectorAll('.gb_g, .gb_h');
    for (const elem of emailElems) {
        const text = elem.textContent || elem.getAttribute('aria-label') || '';
        if (text.includes('@')) {
            return text.trim();
        }
    }
    
    return 'anonymous';
}

// Function to create and inject the WriteWise button
function injectWriteWiseButton() {
    console.log('Attempting to inject WriteWise button');
    
    // Create the button element
    const button = document.createElement('button');
    button.className = 'writewise-button';
    button.innerHTML = `<img src="${chrome.runtime.getURL('logo/logo-16.png')}" alt="WriteWise" width="16" height="16">`;
    button.title = 'WriteWise - Enhance your email';
    
    // Function to find and insert the button
    function insertButton() {
        // Try multiple selectors for the send button
        const sendButtonSelectors = [
            '[role="button"][data-tooltip*="Send"]',
            '[role="button"][data-tooltip*="⌘Enter"]',
            '[data-tooltip-delay="800"]',
            '.T-I.J-J5-Ji.aoO.v7.T-I-atl.L3'
        ];
        
        let sendButton;
        for (const selector of sendButtonSelectors) {
            sendButton = document.querySelector(selector);
            if (sendButton) {
                console.log('Found send button with selector:', selector);
                break;
            }
        }

        if (sendButton && !document.querySelector('.writewise-button')) {
            console.log('Found send button, injecting WriteWise button');
            
            // Find the toolbar
            const toolbar = sendButton.closest('[role="toolbar"]') || sendButton.parentElement;
            if (toolbar) {
                // Insert before the send button's container
                toolbar.insertBefore(button, sendButton);
                console.log('Successfully injected button into toolbar');
            } else {
                // Fallback: insert directly before send button
                sendButton.parentNode.insertBefore(button, sendButton);
                console.log('Injected button using fallback method');
            }
        } else {
            console.log('Send button not found or WriteWise button already exists');
        }
    }

    // Initial insertion attempt
    insertButton();

    // Watch for compose window changes
    const composeObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length || 
                (mutation.type === 'attributes' && 
                 (mutation.attributeName === 'class' || mutation.attributeName === 'style'))) {
                insertButton();
            }
        }
    });

    // Observe both compose window and its parent
    function observeComposeWindows() {
        const composeWindows = document.querySelectorAll('.M9, .AD, .nH.nn');
        composeWindows.forEach(window => {
            composeObserver.observe(window, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class', 'style']
            });
            console.log('Observing compose window:', window);
        });
    }

    // Initial observation
    observeComposeWindows();

    // Also observe the body for new compose windows
    const bodyObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length) {
                observeComposeWindows();
                insertButton();
            }
        }
    });

    bodyObserver.observe(document.body, {
        childList: true,
        subtree: true
    });
    console.log('Observing body for new compose windows');
}

// Function to send data to server
async function sendToServer(data) {
    try {
        console.log('Sending data to server:', data);
        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error sending data to server:', error);
        throw error;
    }
}

// Add click handler
document.addEventListener('click', async (event) => {
    if (event.target.closest('.writewise-button')) {
        const button = event.target.closest('.writewise-button');
        button.style.background = '#666666';
        
        try {
            const data = await getComposeData();
            console.log('Extracted data:', data);
            
            if (data) {
                await sendToServer(data);
                button.style.background = '#4CAF50';
            } else {
                console.error('Failed to extract email data');
                button.style.background = '#FF0000';
            }
        } catch (error) {
            console.error('Error:', error);
            button.style.background = '#FF0000';
        }
        
        setTimeout(() => {
            button.style.background = '#228B22';
        }, 2000);
    }
});

// Initialize when DOM is ready
function initialize() {
    console.log('Initializing WriteWise');
    
    // Wait for jQuery to be available
    if (typeof jQuery === 'undefined') {
        console.log('Waiting for jQuery...');
        setTimeout(initialize, 100);
        return;
    }
    
    if (initializeGmail()) {
        injectWriteWiseButton();
        
        // Also try to inject when Gmail.js signals it's ready
        gmail.observe.on('compose', () => {
            console.log('Gmail compose detected');
            injectWriteWiseButton();
        });
        
        // Additional injection attempt for compose windows
        gmail.observe.on('view_thread', () => {
            console.log('Thread view detected');
            setTimeout(injectWriteWiseButton, 500);
        });
    }
}

// Start initialization
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}

// Also try to initialize after a delay to ensure everything is loaded
setTimeout(initialize, 1000); 