// ============================================
// POST DETAIL PAGE - Complete JavaScript
// Save as: static/js/post-detail.js
// ============================================

// ============================================
// UTILITY FUNCTIONS
// ============================================

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

const csrftoken = getCookie('csrftoken');

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================

function showToast(message, type = 'success') {
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    
    const icons = {
        success: 'check-circle-fill',
        error: 'x-circle-fill',
        warning: 'exclamation-triangle-fill',
        info: 'info-circle-fill'
    };
    
    toast.innerHTML = `
        <div class="toast-content">
            <i class="bi bi-${icons[type] || icons.success}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add CSS for toast if not already in stylesheet
if (!document.getElementById('toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        .toast-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            z-index: 10000;
            opacity: 0;
            transform: translateX(400px);
            transition: all 0.3s ease;
        }
        .toast-notification.show {
            opacity: 1;
            transform: translateX(0);
        }
        .toast-content {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .toast-success { border-left: 4px solid #10b981; }
        .toast-error { border-left: 4px solid #ef4444; }
        .toast-warning { border-left: 4px solid #f59e0b; }
        .toast-info { border-left: 4px solid #3b82f6; }
        .toast-success i { color: #10b981; }
        .toast-error i { color: #ef4444; }
        .toast-warning i { color: #f59e0b; }
        .toast-info i { color: #3b82f6; }
    `;
    document.head.appendChild(style);
}

// ============================================
// LIKE FUNCTIONALITY
// ============================================

window.toggleLike = function(button) {
    if (!window.postData || !window.postData.isAuthenticated) {
        window.location.href = `/account/login/?next=${window.location.pathname}`;
        return;
    }

    const postId = button.getAttribute('data-post-id');
    button.classList.add('loading');
    button.disabled = true;
    
    fetch('/ajax/like/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ post_id: postId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const icon = button.querySelector('i');
            const text = button.querySelector('#like-text');
            const count = button.querySelector('#like-count');
            
            const heroLikes = document.getElementById('hero-likes');
            const sidebarLikes = document.getElementById('sidebar-likes');
            
            if (data.liked) {
                icon.classList.remove('bi-heart');
                icon.classList.add('bi-heart-fill');
                button.classList.add('liked');
                if (text) text.textContent = 'Liked';
            } else {
                icon.classList.remove('bi-heart-fill');
                icon.classList.add('bi-heart');
                button.classList.remove('liked');
                if (text) text.textContent = 'Like';
            }
            
            if (count) count.textContent = data.likes_count;
            if (heroLikes) heroLikes.textContent = data.likes_count;
            if (sidebarLikes) sidebarLikes.textContent = data.likes_count;
            
            showToast(data.message, 'success');
        } else {
            showToast(data.error || 'Failed to update like', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        button.classList.remove('loading');
        button.disabled = false;
    });
}

// ============================================
// FOLLOW FUNCTIONALITY
// ============================================

window.toggleFollow = function(button) {
    const authorId = button.getAttribute('data-author-id');
    button.classList.add('loading');
    button.disabled = true;
    
    fetch('/ajax/follow/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ author_id: authorId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.following) {
                button.classList.add('liked');
                button.innerHTML = '<i class="bi bi-person-dash-fill"></i> Unfollow';
            } else {
                button.classList.remove('liked');
                button.innerHTML = '<i class="bi bi-person-plus-fill"></i> Follow';
            }
            showToast(data.message, 'success');
        } else {
            showToast(data.error || 'Failed to update follow status', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        button.classList.remove('loading');
        button.disabled = false;
    });
}

// ============================================
// COMMENT REPLY FUNCTIONALITY
// ============================================

window.toggleReplyForm = function(commentId) {
    const replyForm = document.getElementById(`replyForm${commentId}`);
    
    if (replyForm) {
        document.querySelectorAll('.reply-form').forEach(form => {
            if (form.id !== `replyForm${commentId}`) {
                form.style.display = 'none';
            }
        });
        
        if (replyForm.style.display === 'none' || !replyForm.style.display) {
            replyForm.style.display = 'block';
            const textarea = replyForm.querySelector('.reply-textarea');
            if (textarea) {
                setTimeout(() => textarea.focus(), 100);
            }
        } else {
            replyForm.style.display = 'none';
        }
    }
}

window.submitReply = function(commentId) {
    const replyForm = document.getElementById(`replyForm${commentId}`);
    const textarea = replyForm.querySelector('.reply-textarea');
    const replyText = textarea.value.trim();
    
    if (!replyText) {
        showToast('Please write a reply before submitting', 'error');
        textarea.focus();
        return;
    }
    
    if (replyText.length < 5) {
        showToast('Reply must be at least 5 characters long', 'error');
        textarea.focus();
        return;
    }
    
    if (replyText.length > 500) {
        showToast('Reply cannot exceed 500 characters', 'error');
        return;
    }
    
    const submitBtn = replyForm.querySelector('.modern-btn');
    if (submitBtn) {
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Posting...';
    }
    
    fetch('/ajax/reply/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            comment_id: commentId,
            reply_text: replyText
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const reply = data.reply;
            
            const replyHTML = `
                <div class="reply-modern" data-comment-id="${reply.id}">
                    <div class="comment-header-modern">
                        <div class="modern-avatar small">
                            ${reply.author_initials}
                        </div>
                        <div class="comment-meta-modern">
                            <div class="comment-author-modern">${escapeHtml(reply.author_name)}</div>
                            <div class="comment-date-modern">Just now</div>
                        </div>
                        ${reply.is_author ? `
                        <div class="comment-actions-modern">
                            <button class="comment-action-btn" onclick="editComment(${reply.id})">
                                <i class="bi bi-pencil-fill"></i>
                            </button>
                            <button class="comment-action-btn delete" onclick="deleteComment(${reply.id})">
                                <i class="bi bi-trash-fill"></i>
                            </button>
                        </div>
                        ` : ''}
                    </div>
                    <div class="comment-body-modern">
                        <p>${escapeHtml(reply.body)}</p>
                    </div>
                </div>
            `;
            
            const parentComment = document.querySelector(`[data-comment-id="${commentId}"]`);
            let repliesContainer = parentComment.querySelector('.comment-replies-modern');
            
            if (!repliesContainer) {
                repliesContainer = document.createElement('div');
                repliesContainer.className = 'comment-replies-modern';
                const replyFormElement = parentComment.querySelector('.reply-form');
                if (replyFormElement) {
                    parentComment.insertBefore(repliesContainer, replyFormElement);
                } else {
                    parentComment.appendChild(repliesContainer);
                }
            }
            
            repliesContainer.insertAdjacentHTML('beforeend', replyHTML);
            textarea.value = '';
            replyForm.style.display = 'none';
            showToast('Reply posted successfully!', 'success');
            
            const newReply = repliesContainer.lastElementChild;
            newReply.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            showToast(data.error || 'Failed to post reply', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        if (submitBtn) {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-send-fill"></i> Reply';
        }
    });
}

// ============================================
// COMMENT EDIT FUNCTIONALITY
// ============================================

window.editComment = function(commentId) {
    const commentElement = document.querySelector(`[data-comment-id="${commentId}"]`);
    if (!commentElement) {
        showToast('Comment not found', 'error');
        return;
    }
    
    const commentBody = commentElement.querySelector('.comment-body-modern');
    if (!commentBody) {
        showToast('Comment body not found', 'error');
        return;
    }
    
    const paragraph = commentBody.querySelector('p');
    const currentText = paragraph ? paragraph.textContent.trim() : commentBody.textContent.trim();
    commentElement.dataset.originalContent = currentText;
    
    const editForm = `
        <div class="edit-form">
            <textarea class="modern-textarea" style="min-height: 80px;">${escapeHtml(currentText)}</textarea>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                <button class="modern-btn" onclick="saveCommentEdit(${commentId})" style="padding: 0.625rem 1.5rem;">
                    <i class="bi bi-check2"></i> Save
                </button>
                <button class="comment-action-btn" onclick="cancelCommentEdit(${commentId})" style="padding: 0.625rem 1rem;">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    commentBody.innerHTML = editForm;
    const textarea = commentBody.querySelector('textarea');
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
}

window.saveCommentEdit = function(commentId) {
    const commentElement = document.querySelector(`[data-comment-id="${commentId}"]`);
    const textarea = commentElement.querySelector('.edit-form textarea');
    const newText = textarea.value.trim();
    
    if (!newText) {
        showToast('Comment cannot be empty', 'error');
        textarea.focus();
        return;
    }
    
    if (newText.length < 10) {
        showToast('Comment must be at least 10 characters long', 'error');
        textarea.focus();
        return;
    }
    
    const saveBtn = commentElement.querySelector('.modern-btn');
    if (saveBtn) {
        saveBtn.classList.add('loading');
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';
    }
    
    fetch('/ajax/edit-comment/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            comment_id: commentId,
            new_text: newText
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const commentBody = commentElement.querySelector('.comment-body-modern');
            commentBody.innerHTML = `<p>${escapeHtml(newText)}</p>`;
            showToast('Comment updated successfully!', 'success');
            delete commentElement.dataset.originalContent;
        } else {
            showToast(data.error || 'Failed to update comment', 'error');
            cancelCommentEdit(commentId);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred. Please try again.', 'error');
        cancelCommentEdit(commentId);
    });
}

window.cancelCommentEdit = function(commentId) {
    const commentElement = document.querySelector(`[data-comment-id="${commentId}"]`);
    const originalContent = commentElement.dataset.originalContent;
    const commentBody = commentElement.querySelector('.comment-body-modern');
    
    if (originalContent) {
        commentBody.innerHTML = `<p>${escapeHtml(originalContent)}</p>`;
        delete commentElement.dataset.originalContent;
    }
}

// ============================================
// COMMENT DELETE FUNCTIONALITY
// ============================================

window.deleteComment = function(commentId) {
    if (!confirm('Are you sure you want to delete this comment? This action cannot be undone.')) {
        return;
    }
    
    const commentElement = document.querySelector(`[data-comment-id="${commentId}"]`);
    commentElement.style.transition = 'all 0.3s ease';
    commentElement.style.opacity = '0.5';
    
    fetch('/ajax/delete-comment/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ comment_id: commentId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            commentElement.style.opacity = '0';
            commentElement.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                commentElement.remove();
                showToast('Comment deleted successfully!', 'success');
            }, 300);
        } else {
            commentElement.style.opacity = '1';
            showToast(data.error || 'Failed to delete comment', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        commentElement.style.opacity = '1';
        showToast('An error occurred. Please try again.', 'error');
    });
}

// ============================================
// COPY TO CLIPBOARD
// ============================================

window.copyToClipboard = function(event, url) {
    event.preventDefault();
    
    navigator.clipboard.writeText(url).then(function() {
        const btn = event.target.closest('button');
        const originalHTML = btn.innerHTML;
        
        btn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
        btn.style.background = 'var(--success)';
        btn.style.color = 'white';
        
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.background = '';
            btn.style.color = '';
        }, 2000);
        
        showToast('Link copied to clipboard!', 'success');
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        showToast('Failed to copy link', 'error');
    });
}

// ============================================
// COMMENT FORM SUBMISSION (NO URL HASH)
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Post detail page initialized');
    
    // Remove hash from URL if present
    if (window.location.hash) {
        history.replaceState(null, null, window.location.pathname + window.location.search);
    }
    
    // Handle comment form submission
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submit-comment-btn');
            const textarea = document.getElementById('comment-body');
            const errorDiv = document.getElementById('comment-error');
            const commentText = textarea.value.trim();
            
            // Validation
            if (commentText.length < 10) {
                if (errorDiv) {
                    errorDiv.textContent = 'Comment must be at least 10 characters long';
                    errorDiv.style.display = 'block';
                }
                textarea.focus();
                return;
            }
            
            // Hide error
            if (errorDiv) errorDiv.style.display = 'none';
            
            // Disable submit button
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Posting...';
            
            // Get CSRF token
            const csrfInput = commentForm.querySelector('[name=csrfmiddlewaretoken]');
            const csrfValue = csrfInput ? csrfInput.value : csrftoken;
            
            // Submit via AJAX
            fetch(window.location.pathname, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfValue
                },
                body: `body=${encodeURIComponent(commentText)}`
            })
            .then(response => {
                if (response.redirected || response.ok) {
                    // Success - reload without hash
                    showToast('Comment posted successfully!', 'success');
                    setTimeout(() => {
                        window.location.href = window.location.pathname;
                    }, 500);
                    return;
                }
                return response.text();
            })
            .catch(error => {
                console.error('Error:', error);
                if (errorDiv) {
                    errorDiv.textContent = 'Failed to post comment. Please try again.';
                    errorDiv.style.display = 'block';
                }
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-send-fill"></i> Post Comment';
            });
        });
    }
    
    // Attach like button event
    const likeBtn = document.getElementById('like-button');
    if (likeBtn) {
        likeBtn.addEventListener('click', function() {
            toggleLike(this);
        });
    }
});