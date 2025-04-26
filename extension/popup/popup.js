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

    // Listen for button press events from content script
    chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
        if (request.type === 'BUTTON_PRESSED') {
            updateButtonPressCount();
        }
    });
}

function updateButtonPressCount() {
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