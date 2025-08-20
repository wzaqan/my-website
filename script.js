document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('embassy-form');
    const modal = document.getElementById('success-modal');
    const closeBtn = document.querySelector('.close');
    const formGroups = document.querySelectorAll('.form-group');
    
    // إضافة تأثير التركيز على حقول النموذج
    formGroups.forEach(group => {
        const input = group.querySelector('input, textarea');
        
        input.addEventListener('focus', () => {
            group.classList.add('highlight');
        });
        
        input.addEventListener('blur', () => {
            group.classList.remove('highlight');
        });
    });
    
    // التحقق من صحة النموذج
    function validateForm() {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        // إزالة رسائل الخطأ السابقة
        document.querySelectorAll('.error-message').forEach(el => el.remove());
        document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('error');
                
                const errorMessage = document.createElement('div');
                errorMessage.className = 'error-message';
                errorMessage.innerHTML = `
                    <span class="ar">هذا الحقل مطلوب</span>
                    <span class="en">This field is required</span>
                `;
                
                field.parentNode.appendChild(errorMessage);
            }
        });
        
        // التحقق من صحة البريد الإلكتروني
        const emailField = document.getElementById('email');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (emailField.value.trim() && !emailRegex.test(emailField.value)) {
            isValid = false;
            emailField.classList.add('error');
            
            const errorMessage = document.createElement('div');
            errorMessage.className = 'error-message';
            errorMessage.innerHTML = `
                <span class="ar">يرجى إدخال بريد إلكتروني صحيح</span>
                <span class="en">Please enter a valid email address</span>
            `;
            
            emailField.parentNode.appendChild(errorMessage);
        }
        
        return isValid;
    }
    
    // إرسال النموذج
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        // جمع بيانات النموذج
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        // إعداد محتوى البريد الإلكتروني
        const emailContent = prepareEmailContent(data);
        
        // إنشاء رابط mailto لإرسال البريد الإلكتروني
        const mailtoLink = `mailto:wzaqan@gmail.com?subject=${encodeURIComponent('إجابات أسئلة السفارة الأمريكية / American Embassy Questions Answers')}&body=${encodeURIComponent(emailContent)}`;
        
        // فتح تطبيق البريد الإلكتروني الافتراضي
        window.location.href = mailtoLink;
        
        // إظهار رسالة النجاح
        setTimeout(() => {
            modal.style.display = 'block';
            form.reset();
        }, 1000);
    })
    });
    
    // إعداد محتوى البريد الإلكتروني
    function prepareEmailContent(data) {
        const questions = [
            'ما هو الغرض من زيارتك للولايات المتحدة الأمريكية؟ / What is the purpose of your visit to the United States?',
            'هل سبق لك زيارة الولايات المتحدة من قبل؟ إذا كان الجواب نعم، متى وما كان الغرض من الزيارة؟ / Have you visited the United States before? If yes, when and what was the purpose of the visit?',
            'هل لديك أقارب في الولايات المتحدة؟ إذا كان الجواب نعم، يرجى ذكر صلة القرابة وحالة الإقامة. / Do you have relatives in the United States? If yes, please mention the relationship and residency status.',
            'ما هي مؤهلاتك التعليمية وخبراتك المهنية؟ / What are your educational qualifications and professional experiences?',
            'كم المدة التي تخطط لقضائها في الولايات المتحدة؟ / How long do you plan to stay in the United States?'
        ];
        
        let content = `
            الاسم بالعربية / Arabic Name: ${data.fullNameAr}\n
            الاسم بالإنجليزية / English Name: ${data.fullNameEn}\n
            البريد الإلكتروني / Email: ${data.email}\n
            رقم الهاتف / Phone Number: ${data.phone}\n\n
            --- الإجابات / Answers ---\n\n
        `;
        
        for (let i = 0; i < 5; i++) {
            content += `${i+1}. ${questions[i]}\n
            ${data['question' + (i+1)]}\n\n
`;
        }
        
        return content;
    }
    
    // إغلاق النافذة المنبثقة
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // إغلاق النافذة المنبثقة عند النقر خارجها
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// إضافة تأثيرات إضافية للنموذج
document.addEventListener('DOMContentLoaded', function() {
    // إضافة تأثير التمرير السلس
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});