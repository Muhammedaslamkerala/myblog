// Main JavaScript for MyBlog
document.addEventListener('DOMContentLoaded', function() {
    initializeScrollToTop();
    initializeNavigation();
    initializeSearch();
    initializeLikeButtons();
    initializeNewsletterForm();
    
    // Initialize AOS if available
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-in-out',
            once: true
        });
    }
});

// Scroll to Top Functionality
function initializeScrollToTop() {
    const fab = document.querySelector('.fab');
    if (!fab) return;

    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            fab.classList.add('show');
        } else {
            fab.classList.remove('show');
        }
    });
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Navigation
function initializeNavigation() {
    // Mobile menu toggle
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navbarToggler.contains(e.target) && !navbarCollapse.contains(e.target)) {
                navbarCollapse.classList.remove('show');
            }
        });
    }
}

// Search Functionality
function initializeSearch() {
    const searchForms = document.querySelectorAll('form[action*="search"]');
    
    searchForms.forEach(form => {
        const searchInput = form.querySelector('input[name="q"]');
        
        if (searchInput) {
            // Add search suggestions (if needed)
            searchInput.addEventListener('input', function() {
                const query = this.value.trim();
                if (query.length > 2) {
                    // Could implement search suggestions here
                    console.log('Searching for:', query);
                }
            });
        }
    });
}

// Like Buttons (AJAX)
function initializeLikeButtons() {
    const likeButtons = document.querySelectorAll('.like-btn, .btn-like');
    
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (!isUserAuthenticated()) {
                showLoginModal();
                return;
            }
            
            const postId = this.dataset.postId || this.dataset.id;
            if (!postId) return;
            
            likePost(postId, this);
        });
    });
}

function likePost(postId, button) {
    const isLiked = button.classList.contains('liked');
    
    // Optimistic UI update
    toggleLikeButton(button, !isLiked);
    
    fetch('/api/like-post/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            post_id: postId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toggleLikeButton(button, data.liked);
            updateLikeCount(button, data.likes_count);
        } else {
            // Revert optimistic update on error
            toggleLikeButton(button, isLiked);
            showError('Failed to update like status');
        }
    })
    .catch(error => {
        // Revert optimistic update on error
        toggleLikeButton(button, isLiked);
        showError('Network error occurred');
        console.error('Like error:', error);
    });
}

function toggleLikeButton(button, isLiked) {
    const icon = button.querySelector('i');
    
    if (isLiked) {
        button.classList.add('liked', 'btn-danger');
        button.classList.remove('btn-outline-danger');
        if (icon) {
            icon.className = 'bi bi-heart-fill';
        }
    } else {
        button.classList.remove('liked', 'btn-danger');
        button.classList.add('btn-outline-danger');
        if (icon) {
            icon.className = 'bi bi-heart';
        }
    }
}

function updateLikeCount(button, count) {
    const countElement = button.querySelector('.like-count');
    if (countElement) {
        countElement.textContent = count;
    }
    
    // Update count in nearby elements
    const parentCard = button.closest('.blog-card, .post-card');
    if (parentCard) {
        const statsElement = parentCard.querySelector('.stat-item:has(.bi-heart)');
        if (statsElement) {
            statsElement.innerHTML = `<i class="bi bi-heart"></i> ${count}`;
        }
    }
}

// Newsletter Form
function initializeNewsletterForm() {
    const newsletterForm = document.querySelector('.newsletter-form');
    
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const emailInput = this.querySelector('input[type="email"]');
            const email = emailInput.value.trim();
            
            if (!isValidEmail(email)) {
                showError('Please enter a valid email address');
                return;
            }
            
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            submitButton.textContent = 'Subscribing...';
            submitButton.disabled = true;
            
            // Simulate newsletter subscription (replace with actual API call)
            setTimeout(() => {
                showSuccess('Thank you for subscribing to our newsletter!');
                emailInput.value = '';
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }, 1000);
        });
    }
}

// Counter Animation
function initializeCounters() {
    const counters = document.querySelectorAll('[data-count]');
    
    const animateCounter = (counter) => {
        const target = parseInt(counter.getAttribute('data-count'));
        const increment = target / 100;
        let current = 0;
        
        const updateCounter = () => {
            if (current < target) {
                current += increment;
                counter.textContent = Math.floor(current).toLocaleString();
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target.toLocaleString();
            }
        };
        
        updateCounter();
    };
    
    // Intersection Observer for counter animation
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
                entry.target.classList.add('animated');
                animateCounter(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => {
        observer.observe(counter);
    });
}

// Utility Functions
function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    
    // Fallback: try to get from meta tag
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    return metaToken ? metaToken.content : '';
}

function isUserAuthenticated() {
    // Check if user is authenticated (you might have a global variable or check a specific element)
    return document.body.dataset.userAuthenticated === 'true' || 
           document.querySelector('.user-menu') !== null;
}

function showLoginModal() {
    // Redirect to login page or show modal
    window.location.href = '/accounts/login/?next=' + encodeURIComponent(window.location.pathname);
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showSuccess(message) {
    showMessage(message, 'success');
}

function showError(message) {
    showMessage(message, 'danger');
}

function showMessage(message, type = 'info') {
    // Create toast/alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to messages container or create one
    let messagesContainer = document.querySelector('.messages-container');
    if (!messagesContainer) {
        messagesContainer = document.createElement('div');
        messagesContainer.className = 'messages-container';
        document.body.appendChild(messagesContainer);
    }
    
    messagesContainer.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Image Loading with Fallback
function handleImageError(img) {
    // Set a default image when original fails to load
    img.src = 'https://via.placeholder.com/400x250/f1f5f9/64748b?text=Image+Not+Available';
    img.onerror = null; // Prevent infinite loop
}

// Smooth Scrolling for Anchor Links
document.addEventListener('click', function(e) {
    const link = e.target.closest('a[href^="#"]');
    if (link) {
        e.preventDefault();
        const targetId = link.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
});

// Form Validation Enhancement
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateInput(this);
            });
            
            input.addEventListener('input', function() {
                // Remove error state on input
                this.classList.remove('is-invalid');
                const errorElement = this.parentNode.querySelector('.invalid-feedback');
                if (errorElement) {
                    errorElement.remove();
                }
            });
        });
    });
}

function validateInput(input) {
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required field validation
    if (input.required && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Email validation
    if (input.type === 'email' && value && !isValidEmail(value)) {
        isValid = false;
        errorMessage = 'Please enter a valid email address';
    }
    
    // URL validation
    if (input.type === 'url' && value && !isValidURL(value)) {
        isValid = false;
        errorMessage = 'Please enter a valid URL';
    }
    
    // Update input state
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        
        // Add error message
        let errorElement = input.parentNode.querySelector('.invalid-feedback');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            input.parentNode.appendChild(errorElement);
        }
        errorElement.textContent = errorMessage;
    }
    
    return isValid;
}

function isValidURL(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

// Initialize enhanced form validation when DOM is loaded
document.addEventListener('DOMContentLoaded', enhanceFormValidation);

// Export functions for use in other scripts
window.MyBlog = {
    scrollToTop,
    likePost,
    showSuccess,
    showError,
    showMessage,
    initializeCounters,
    isUserAuthenticated,
    getCSRFToken
};