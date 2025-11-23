// Post Write JavaScript
let selectedTags = [];

document.addEventListener('DOMContentLoaded', function() {
    setupSubmit();
    setupImageUpload();
    initializeTags();
});

function setupSubmit() {
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const actionField = document.getElementById('formAction');
            if (actionField) actionField.value = 'publish';
            if (validateForm()) {
                document.getElementById('postForm').submit();
            }
        });
    }
}

function validateForm() {
    const title = document.getElementById('id_title').value.trim();
    
    if (!title || title.length < 3) {
        alert('Please enter a title (minimum 3 characters)');
        return false;
    }
    
    // Check if at least one category is selected
    const categories = document.querySelectorAll('input[name="categories"]:checked');
    if (categories.length === 0) {
        alert('Please select at least one category');
        return false;
    }
    
    return true;
}

// removed writing stats

function setupImageUpload() {
    const fileInput = document.getElementById('id_featured_image');
    const imageUpload = document.getElementById('imageUpload');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const removeImageBtn = document.getElementById('removeImage');

    if (!fileInput || !imageUpload) return;

    // Click to upload
    imageUpload.addEventListener('click', function(e) {
        if (!e.target.closest('#removeImage')) {
            fileInput.click();
        }
    });

    // Drag and drop
    imageUpload.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    imageUpload.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    imageUpload.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                alert('Please select an image file.');
            }
        }
    });

    // File input change
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file.');
                this.value = '';
                return;
            }
            
            if (file.size > 10 * 1024 * 1024) {
                alert('File size must be less than 10MB.');
                this.value = '';
                return;
            }
            
            const reader = new FileReader();
            reader.onload = function(e) {
                showImagePreview(e.target.result);
            };
            reader.readAsDataURL(file);
        }
    });

    // Remove image
    if (removeImageBtn) {
        removeImageBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            e.preventDefault();
            removeImage();
        });
    }
}

function showImagePreview(src) {
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const uploadPrompt = document.getElementById('uploadPrompt');

    if (previewImg && imagePreview && uploadPrompt) {
        previewImg.src = src;
        imagePreview.style.display = 'block';
        uploadPrompt.style.display = 'none';
    }
}

function removeImage() {
    const imagePreview = document.getElementById('imagePreview');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const featuredImage = document.getElementById('id_featured_image');

    if (imagePreview && uploadPrompt && featuredImage) {
        imagePreview.style.display = 'none';
        uploadPrompt.style.display = 'flex';
        featuredImage.value = '';
    }
}

// Tags functionality
function initializeTags() {
    const tagsInput = document.getElementById('tagsInput');
    const tagInput = document.getElementById('tagInput');
    const hiddenTagsInput = document.getElementById('tags_input');
    
    // Load existing tags
    if (hiddenTagsInput && hiddenTagsInput.value) {
        const existingTags = hiddenTagsInput.value.split(',').map(t => t.trim()).filter(t => t);
        existingTags.forEach(tag => addTag(tag, false));
    }
    
    // Show input on click
    if (tagsInput && tagInput) {
        tagInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                const tagName = this.value.trim();
                if (tagName) {
                    addTag(tagName);
                    this.value = '';
                }
            } else if (e.key === 'Backspace' && this.value === '' && selectedTags.length > 0) {
                removeTag(selectedTags[selectedTags.length - 1]);
            }
        });
    }
}

function addTag(tagName, updateHidden = true) {
    tagName = tagName.trim();
    if (!tagName || selectedTags.includes(tagName)) return;
    
    selectedTags.push(tagName);
    
    const tagsInput = document.getElementById('tagsInput');
    const tagElement = document.createElement('div');
    tagElement.className = 'tag-item';
    tagElement.innerHTML = `
        ${tagName}
        <button type="button" class="tag-remove" onclick="removeTag('${tagName}')">
            <i class="bi bi-x"></i>
        </button>
    `;
    
    // Insert before the input
    const tagInput = document.getElementById('tagInput');
    tagsInput.insertBefore(tagElement, tagInput);
    
    if (updateHidden) {
        updateHiddenTagsInput();
    }
}

function removeTag(tagName) {
    const index = selectedTags.indexOf(tagName);
    if (index > -1) {
        selectedTags.splice(index, 1);
        
        // Remove from DOM
        const tagsInput = document.getElementById('tagsInput');
        const tagElements = tagsInput.querySelectorAll('.tag-item');
        tagElements.forEach(el => {
            if (el.textContent.trim().replace(/×/g, '').trim() === tagName) {
                el.remove();
            }
        });
        
        updateHiddenTagsInput();
    }
}

function updateHiddenTagsInput() {
    const hiddenInput = document.getElementById('tags_input');
    if (hiddenInput) {
        hiddenInput.value = selectedTags.join(',');
    }
}

function addPopularTag(tagName) {
    if (!selectedTags.includes(tagName)) {
        addTag(tagName);
    }
}

// AI Assistant toggle
const aiToggle = document.getElementById('aiToggle');
const aiPanel = document.getElementById('aiPanel');

if (aiToggle && aiPanel) {
    aiToggle.addEventListener('click', function() {
        aiPanel.classList.toggle('show');
    });
}

function aiSuggest(type) {
    alert('AI feature coming soon! Type: ' + type);
}