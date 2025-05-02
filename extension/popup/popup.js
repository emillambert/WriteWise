import gmailService from '../services/gmailService.js';

// Check if user is signed in when popup opens
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Check for Google auth token
        const token = await chrome.identity.getAuthToken({ interactive: false });
        if (token) {
            // Get user profile information
            const profile = await getUserProfile(token.token);
            showMenuSection(profile);
            initializeProgressBar();
        } else {
            showSignInSection();
        }
    } catch (error) {
        console.error('Error checking auth state:', error);
        showSignInSection();
    }
});

async function getUserProfile(token) {
    try {
        const response = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            throw new Error('Failed to fetch user profile');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching user profile:', error);
        return null;
    }
}

function showMenuSection(profile) {
    document.getElementById('signin-section').style.display = 'none';
    document.getElementById('menu-section').style.display = 'block';
    
    if (profile) {
        // Set profile picture
        const profilePicture = document.getElementById('profilePicture');
        profilePicture.src = profile.picture || '';
        profilePicture.alt = profile.name || 'Profile';
        
        // Set profile name (first name only)
        const profileName = document.getElementById('profileName');
        const firstName = profile.given_name || profile.name || 'User';
        profileName.textContent = firstName;
    }
}

function showSignInSection() {
    document.getElementById('menu-section').style.display = 'none';
    document.getElementById('signin-section').style.display = 'flex';
}

// Add sign-out button click handler
document.getElementById('signOutBtn')?.addEventListener('click', async function() {
    try {
        // Send sign out message to service worker
        chrome.runtime.sendMessage({ type: 'GOOGLE_SIGN_OUT' }, function(response) {
            // Show sign-in section after sign out completes
            showSignInSection();
        });
    } catch (error) {
        console.error('Sign out error:', error);
        // Still show sign-in section even if there's an error
        showSignInSection();
    }
});

// Progress bar functionality
function initializeProgressBar() {
    // Get or initialize daily usage data
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(['dailyUsage'], function(result) {
            const today = new Date().toDateString();
            let dailyUsage = result.dailyUsage || { date: today, count: 0 };

            // Reset if it's a new day
            if (dailyUsage.date !== today) {
                dailyUsage = { date: today, count: 0 };
                chrome.storage.local.set({ dailyUsage });
            }

            updateProgressBar(dailyUsage.count);
        });
    } else {
        console.error('chrome.storage.local is not available');
        updateProgressBar(0);
    }

    // Listen for button press events from content script
    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
        if (request.type === 'BUTTON_PRESSED') {
            updateButtonPressCount();
        }
    });
}

function updateButtonPressCount() {
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
                updateProgressBar(dailyUsage.count);
            }
        });
    } else {
        console.error('chrome.storage.local is not available');
        updateProgressBar(0);
    }
}

function updateProgressBar(count) {
    const progressFill = document.querySelector('.progress-circle-fill');
    const progressCount = document.querySelector('.progress-count');
    
    if (progressFill && progressCount) {
        const percentage = (count / 10) * 100;
        const offset = 100 - percentage;
        
        progressFill.style.strokeDashoffset = offset;
        progressCount.textContent = count;
    }
}

// Helper function to deduplicate emails by ID
function deduplicateEmails(emails) {
    const uniqueEmails = {};
    for (const email of emails) {
        if (email.id && !uniqueEmails[email.id]) {
            uniqueEmails[email.id] = email;
        }
    }
    return Object.values(uniqueEmails);
}

async function sendEmailsToServer(emails, userId) {
    // Deduplicate emails before sending
    const uniqueEmails = deduplicateEmails(emails);
    console.log(`Deduplicated ${emails.length} emails to ${uniqueEmails.length} unique emails`);
    
    const timestamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 15);
    const safeUserId = typeof userId === 'string' ? userId.replace(/[@.]/g, '_') : 'anonymous';
    const data = {
        user_id: userId,
        emails: uniqueEmails
    };
    
    const response = await fetch('http://localhost:27481/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response.ok;
}

async function getUserEmailFallback() {
    return new Promise((resolve) => {
        if (chrome.identity && chrome.identity.getProfileUserInfo) {
            chrome.identity.getProfileUserInfo({accountStatus: 'ANY'}, function(userInfo) {
                resolve(userInfo.email || null);
            });
        } else {
            resolve(null);
        }
    });
}

document.getElementById('analyzeBtn')?.addEventListener('click', async function() {
    try {
        const emails = await gmailService.getLastSentEmails(500); // Increased to 500 to ensure we have enough after filtering
        const token = await gmailService.getAccessToken();
        const userProfile = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(res => res.json());
        let userId = userProfile.email;
        if (!userId) {
            userId = await getUserEmailFallback();
        }
        userId = userId || 'anonymous';
        await sendEmailsToServer(emails, userId);
        
        // Show success message
        const statusElem = document.getElementById('statusMessage');
        if (statusElem) {
            statusElem.textContent = 'Analysis complete!';
            statusElem.style.color = '#4CAF50';
            setTimeout(() => {
                statusElem.textContent = '';
            }, 3000);
        }
    } catch (error) {
        console.error('Failed to analyze emails:', error);
        const statusElem = document.getElementById('statusMessage');
        if (statusElem) {
            statusElem.textContent = 'Failed to analyze emails: ' + error.message;
            statusElem.style.color = '#FF0000';
        }
    }
}); 