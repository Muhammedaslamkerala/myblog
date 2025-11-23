// ============================================
// MAIN.JS - Global JavaScript for MyBlog
// Save as: static/js/main.js
// ============================================

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('MyBlog initialized');
    
    // Initialize AOS (Animate On Scroll)
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-in-out',
            once: true,
            offset: 100
        });
    }
    
    // Initialize all features
    initScrollToTop();
    initSearchFunctionality();
    initNavbarScroll();
    initDropdowns();
    autoHideMessages();
});

// ============================================
// SCROLL TO TOP FUNCTIONALITY
// ============================================

function initScrollToTop() {
    const scrollBtn = document.querySelector('.fab');
    
    if (scrollBtn) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollBtn.style.display = 'flex';
            } else {
                scrollBtn.style.display = 'none';
            }
        });
    }
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// ============================================
// NAVBAR SCROLL EFFECT
// ============================================

function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    
    if (navbar) {
        let lastScroll = 0;
        
        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > 100) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
            
            lastScroll = currentScroll;
        });
    }
}

// ============================================
// SEARCH FUNCTIONALITY
// ============================================

function initSearchFunctionality() {
    const searchInput = document.querySelector('.search-input');
    const searchForm = document.querySelector('.search-container form');
    
    if (searchInput && searchForm) {
        // Auto-submit on Enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (this.value.trim().length >= 3) {
                    searchForm.submit();
                }
            }
        });
        
        // Clear button functionality (if you want to add one)
        searchInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                this.classList.add('has-content');
            } else {
                this.classList.remove('has-content');
            }
        });
    }
}

// ============================================
// DROPDOWN ENHANCEMENTS
// ============================================

function initDropdowns() {
    // Add smooth animations to Bootstrap dropdowns
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', function(e) {
            const menu = this.nextElementSibling;
            if (menu && menu.classList.contains('dropdown-menu')) {
                menu.style.animation = 'fadeIn 0.3s ease';
            }
        });
    });
}

// ============================================
// AUTO-HIDE MESSAGES
// ============================================

function autoHideMessages() {
    const messages = document.querySelectorAll('.messages-container .alert');
    
    messages.forEach(message => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(message);
            bsAlert.close();
        }, 5000);
    });
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

// Get CSRF Token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Truncate text
function truncateText(text, length) {
    if (text.length <= length) return text;
    return text.substr(0, length) + '...';
}

// ============================================
// LOADING STATES
// ============================================

function showLoading(element) {
    if (element) {
        element.classList.add('loading');
        element.disabled = true;
    }
}

function hideLoading(element) {
    if (element) {
        element.classList.remove('loading');
        element.disabled = false;
    }
}

// ============================================
// COPY TO CLIPBOARD
// ============================================

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        return Promise.resolve();
    }
}

// ============================================
// SHARE FUNCTIONALITY
// ============================================

function sharePost(title, url) {
    if (navigator.share) {
        // Use native share if available
        navigator.share({
            title: title,
            url: url
        }).then(() => {
            console.log('Shared successfully');
        }).catch((error) => {
            console.log('Error sharing:', error);
        });
    } else {
        // Fallback to copy link
        copyToClipboard(url).then(() => {
            alert('Link copied to clipboard!');
        });
    }
}

// ============================================
// IMAGE LAZY LOADING
// ============================================

function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// ============================================
// FORM VALIDATION HELPERS
// ============================================

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// ============================================
// SMOOTH SCROLL
// ============================================

function smoothScroll(target) {
    const element = document.querySelector(target);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Handle anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href.length > 1) {
            e.preventDefault();
            smoothScroll(href);
        }
    });
});

// ============================================
// RESPONSIVE HANDLING
// ============================================

let windowWidth = window.innerWidth;

window.addEventListener('resize', debounce(function() {
    const newWidth = window.innerWidth;
    
    // Only trigger on width change (not height for mobile address bar)
    if (newWidth !== windowWidth) {
        windowWidth = newWidth;
        
        // Handle mobile menu
        if (windowWidth > 992) {
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                    toggle: false
                });
                bsCollapse.hide();
            }
        }
    }
}, 250));

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals/dropdowns
    if (e.key === 'Escape') {
        // Close any open dropdowns
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(dropdown => {
            const bsDropdown = bootstrap.Dropdown.getInstance(dropdown.previousElementSibling);
            if (bsDropdown) {
                bsDropdown.hide();
            }
        });
    }
});

// ============================================
// CONSOLE WELCOME MESSAGE
// ============================================

console.log('%c🎨 Welcome to MyBlog!', 'color: #6366f1; font-size: 24px; font-weight: bold;');
console.log('%cBuilt with ❤️ using Django & Modern JavaScript', 'color: #64748b; font-size: 14px;');
console.log('%c⚠️ Warning: This is a browser feature intended for developers. Do not paste any code here unless you understand what it does.', 'color: #ef4444; font-size: 12px;');

// ============================================
// PERFORMANCE MONITORING (Optional)
// ============================================

if (window.performance && window.performance.timing) {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const perfData = window.performance.timing;
            const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.log(`📊 Page loaded in ${pageLoadTime}ms`);
        }, 0);
    });
}

// ============================================
// ERROR HANDLING
// ============================================

window.addEventListener('error', function(e) {
    console.error('Global error caught:', e.error);
    // You could send this to your backend logging service
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    // You could send this to your backend logging service
});

// ============================================
// EXPORT FOR USE IN OTHER SCRIPTS
// ============================================

window.MyBlog = {
    getCookie: getCookie,
    debounce: debounce,
    formatNumber: formatNumber,
    truncateText: truncateText,
    copyToClipboard: copyToClipboard,
    sharePost: sharePost,
    validateEmail: validateEmail,
    validateForm: validateForm,
    smoothScroll: smoothScroll,
    showLoading: showLoading,
    hideLoading: hideLoading
};

// ============================================
// END OF MAIN.JS
// ============================================