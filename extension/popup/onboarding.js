import gmailService from '../services/gmailService.js';

// Section navigation
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
}

// Tutorial slides
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');
const progressDots = document.querySelectorAll('.progress-dot');

function showSlide(n) {
    slides.forEach(slide => slide.classList.remove('active'));
    progressDots.forEach(dot => dot.classList.remove('active'));
    
    currentSlide = n;
    slides[n].classList.add('active');
    progressDots[n].classList.add('active');
}

function nextSlide() {
    if (currentSlide < slides.length - 1) {
        showSlide(currentSlide + 1);
    }
}

function prevSlide() {
    if (currentSlide > 0) {
        showSlide(currentSlide - 1);
    }
}

function openGmail() {
    window.open('https://mail.google.com', '_blank');
}

async function sendEmailsToServer(emails, userId) {
    const timestamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 15);
    const safeUserId = typeof userId === 'string' ? userId.replace(/[@.]/g, '_') : 'anonymous';
    const data = {
        user_id: userId,
        emails: emails
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

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Get Started button
    document.getElementById('getStartedBtn').addEventListener('click', () => {
        showSection('tos-section');
    });

    // TOS section
    const tosCheckbox = document.getElementById('tos');
    const agreeBtn = document.getElementById('agreeBtn');
    const googleSignInBtn = document.getElementById('googleSignInBtn');
    
    tosCheckbox.addEventListener('change', () => {
        agreeBtn.disabled = !tosCheckbox.checked;
        googleSignInBtn.disabled = !tosCheckbox.checked;
    });

    document.getElementById('tosBackBtn').addEventListener('click', () => {
        showSection('get-started-section');
    });

    document.getElementById('agreeBtn').addEventListener('click', () => {
        showSection('signin-section');
    });

    // Sign In section
    document.getElementById('signInBackBtn').addEventListener('click', () => {
        showSection('tos-section');
    });

    document.getElementById('googleSignInBtn').addEventListener('click', async () => {
        try {
            const token = await chrome.identity.getAuthToken({ interactive: true });
            if (token) {
                showSection('analysis-section');
            }
        } catch (error) {
            console.error('Sign in error:', error);
        }
    });

    // Analysis section
    document.getElementById('analysisBackBtn').addEventListener('click', () => {
        showSection('signin-section');
    });

    document.getElementById('analyzeBtn').addEventListener('click', async () => {
        try {
            const emails = await gmailService.getLastSentEmails(100);
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
            showSection('tutorial-section');
        } catch (error) {
            alert('Failed to analyze emails: ' + error.message);
        }
    });

    // Tutorial section
    document.getElementById('prevSlideBtn').addEventListener('click', prevSlide);
    document.getElementById('nextSlideBtn').addEventListener('click', nextSlide);
    document.getElementById('skipTutorialBtn').addEventListener('click', openGmail);
    document.getElementById('tryNowBtn').addEventListener('click', openGmail);

    // Initialize first slide
    showSlide(0);
}); 