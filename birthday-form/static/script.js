document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('picture');
    const imagePreview = document.getElementById('imagePreview');
    const form = document.getElementById('eventForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    const statusMessage = document.getElementById('statusMessage');

    const eventTypeSelect = document.getElementById('event_type_select');
    const customEventGroup = document.getElementById('custom_event_group');
    const customEventInput = document.getElementById('custom_event');

    if (eventTypeSelect) {
        eventTypeSelect.addEventListener('change', function() {
            if (this.value === 'Other') {
                customEventGroup.style.display = 'block';
                customEventInput.required = true;
            } else {
                customEventGroup.style.display = 'none';
                customEventInput.required = false;
            }
        });
    }

    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                imagePreview.style.display = 'block';
                document.querySelector('.file-text').style.display = 'none';
            }
            reader.readAsDataURL(file);
        } else {
            imagePreview.src = '#';
            imagePreview.style.display = 'none';
            document.querySelector('.file-text').style.display = 'block';
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        statusMessage.className = 'status-message';
        statusMessage.textContent = '';
        
        btnText.style.display = 'none';
        loader.style.display = 'block';
        submitBtn.disabled = true;

        const formData = new FormData(form);
        
        // Validation logic
        let isValid = true;
        const requiredFields = [
            document.getElementById('name'),
            document.getElementById('date'),
        ];
        
        // Custom event required if 'Other' is selected
        if (eventTypeSelect && eventTypeSelect.value === 'Other') {
            requiredFields.push(customEventInput);
        }

        // Reset errors
        document.querySelectorAll('.input-error, .file-error').forEach(el => {
            el.classList.remove('input-error', 'file-error');
        });

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('input-error');
                isValid = false;
                
                // Remove error style on input
                field.addEventListener('input', function() {
                    this.classList.remove('input-error');
                }, { once: true });
            }
        });

        // File validation
        const fileLabel = document.querySelector('.file-label');
        if (!fileInput.files || fileInput.files.length === 0) {
            fileLabel.classList.add('file-error');
            isValid = false;
            
            fileInput.addEventListener('change', function() {
                fileLabel.classList.remove('file-error');
            }, { once: true });
        }

        if (!isValid) {
            statusMessage.textContent = 'Please fill out all required fields before submitting.';
            statusMessage.className = 'status-message status-error';
            btnText.style.display = 'block';
            loader.style.display = 'none';
            submitBtn.disabled = false;
            return;
        }

        // Handle custom event type logic
        const eventType = formData.get('event_type_select');
        if (eventType === 'Other') {
            formData.set('event_type', customEventInput.value);
        } else {
            formData.set('event_type', eventType);
        }
        formData.delete('event_type_select');

        try {
            const response = await fetch('/api/submit', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                statusMessage.textContent = 'Successfully submitted event!';
                statusMessage.className = 'status-message status-success';
                form.reset();
                imagePreview.style.display = 'none';
                document.querySelector('.file-text').style.display = 'block';
            } else {
                statusMessage.textContent = result.error || 'Failed to sync. Please try again.';
                statusMessage.className = 'status-message status-error';
            }
        } catch (error) {
            console.error('Error:', error);
            statusMessage.textContent = 'An unexpected error occurred.';
            statusMessage.className = 'status-message status-error';
        } finally {
            btnText.style.display = 'block';
            loader.style.display = 'none';
            submitBtn.disabled = false;
        }
    });
});
