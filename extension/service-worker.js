// Service worker for WriteWise extension

// Handle messages from content scripts and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'ANALYZE_EMAIL') {
        if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
            chrome.storage.local.set({ 
                lastEmailData: message.data,
                lastAnalysisTime: Date.now()
            });
        } else {
            console.error('chrome.storage.local is not available');
        }
        // For now, just acknowledge receipt
        sendResponse({ success: true });
    } else if (message.type === 'BUTTON_PRESSED') {
        if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
            chrome.storage.local.get(['dailyUsage'], function(result) {
                const today = new Date().toDateString();
                let dailyUsage = result.dailyUsage || { date: today, count: 0 };

                // Reset if it's a new day
                if (dailyUsage.date !== today) {
                    dailyUsage = { date: today, count: 0 };
                }

                // Increment count if less than 10
                if (dailyUsage.count < 10) {
                    dailyUsage.count++;
                    chrome.storage.local.set({ dailyUsage });
                }
            });
        } else {
            console.error('chrome.storage.local is not available');
        }
        sendResponse({ success: true });
    } else if (message.type === 'GOOGLE_SIGN_IN') {
        handleGoogleSignIn(sendResponse);
        return true; // Keep the message channel open for async response
    }
    if (message.type === 'GET_USER_INFO') {
        handleGetUserInfo(sendResponse);
        return true;
    }
    if (message.type === 'GET_USER_EMAIL') {
        if (chrome.identity && chrome.identity.getProfileUserInfo) {
            chrome.identity.getProfileUserInfo({accountStatus: 'ANY'}, function(userInfo) {
                sendResponse({ email: userInfo.email || 'anonymous' });
            });
            return true; // Keep the message channel open for async response
        } else {
            sendResponse({ email: 'anonymous' });
        }
    }
});

// Handle Google Sign-In
async function handleGoogleSignIn(sendResponse) {
    try {
        // Get auth token from Chrome extension
        const token = await chrome.identity.getAuthToken({ interactive: true });
        
        // Get user info from Google
        const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const userInfo = await response.json();
        
        // Store user info
        if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
            await chrome.storage.local.set({
                user: {
                    email: userInfo.email,
                    name: userInfo.name,
                    picture: userInfo.picture,
                    googleId: userInfo.sub
                }
            });
        } else {
            console.error('chrome.storage.local is not available');
        }

        sendResponse({ success: true, user: userInfo });
    } catch (error) {
        console.error('Sign in error:', error);
        sendResponse({ 
            success: false, 
            error: error.message
        });
    }
}

// Handle getting user info
async function handleGetUserInfo(sendResponse) {
    try {
        let user;
        if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
            const result = await chrome.storage.local.get('user');
            user = result.user;
        } else {
            console.error('chrome.storage.local is not available');
            user = null;
        }
        if (!user) {
            throw new Error('No user session found');
        }

        sendResponse({ success: true, user });
    } catch (error) {
        console.error('Get user info error:', error);
        sendResponse({ 
            success: false, 
            error: error.message
        });
    }
}

// Handle sign out
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GOOGLE_SIGN_OUT') {
        chrome.identity.getAuthToken({ interactive: false }, function(token) {
            if (token) {
                // Revoke the token
                fetch(`https://accounts.google.com/o/oauth2/revoke?token=${token}`)
                    .then(() => {
                        chrome.identity.removeCachedAuthToken({ token: token });
                        if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
                            chrome.storage.local.remove('user');
                        } else {
                            console.error('chrome.storage.local is not available');
                        }
                        sendResponse({ success: true });
                    })
                    .catch(error => {
                        console.error('Error revoking token:', error);
                        sendResponse({ success: false, error: error.message });
                    });
            } else {
                if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
                    chrome.storage.local.remove('user');
                } else {
                    console.error('chrome.storage.local is not available');
                }
                sendResponse({ success: true });
            }
        });
        return true; // Will respond asynchronously
    }
}); 