// JavaScript لصفحة إدخال الموظف / Employee Entry Page JavaScript

// تحميل الصفحة / Page Load
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    setupEventListeners();
    loadColleges();
    setupLanguageToggle();
    setupVerificationToggle();
});

// تهيئة الصفحة
function initializePage() {
    loadColleges();
    setupFormSubmission();
}

// Language toggle functionality
let isEnglish = false;

const translations = {
    ar: {
        pageTitle: 'نظام إدخال بيانات الموظفين',
        collegeLabel: 'الكلية / College *',
        collegePlaceholder: 'اختر الكلية / Select College',
        nameLabel: 'اسم الموظف / Employee Name *',
        namePlaceholder: 'أدخل اسم الموظف / Enter employee name',
        uniIdLabel: 'الرقم الجامعي / University ID *',
        uniIdPlaceholder: 'أدخل الرقم الجامعي / Enter university ID',
        emailLabel: 'الإيميل / Email *',
        emailPlaceholder: 'أدخل الإيميل / Enter email',
        verificationLabel: 'نوع التفعيل / Activation Type *',
        photoOption: 'رفع صورة / Upload Photo',
        photoSubtitle: 'ارفع صورة شخصية واضحة / Upload a clear personal photo',
        passwordOption: 'رقم سري / Password',
        passwordSubtitle: 'أنشئ رقم سري آمن / Create a secure password',
        photoLabel: 'رفع صورة الموظف / Upload Employee Photo *',
        passwordInstruction1: 'تعليمات الرقم السري / Password Instructions:',
        passwordInstruction2: 'يجب أن يكون 6 أرقام على الأقل / Must be at least 6 digits',
        passwordInstruction3: 'لا يجب أن تكون أرقام متسلسلة / Must not be sequential numbers',
        passwordInstruction4: 'أرقام فقط (0-9) / Numbers only (0-9)',
        passwordLabel: 'الرقم السري / Password *',
        confirmPasswordLabel: 'تأكيد الرقم السري / Confirm Password *',
        passwordPlaceholder: 'أدخل الرقم السري / Enter password',
        submitBtn: 'إرسال البيانات / Submit Data',
        successTitle: '✅ تم إرسال بياناتك بنجاح / Your data has been submitted successfully',
        successText: 'بانتظار المراجعة من قبل الإدارة / Waiting for review by administration',
        photoInstruction1: 'تعليمات الصورة / Photo Instructions:',
        photoInstruction2: 'يجب أن تكون الصورة واضحة / Photo must be clear',
        photoInstruction3: 'خلفية بيضاء أو فاتحة / White or light background',
        photoInstruction4: 'حجم الملف أقل من 5 ميجابايت / File size less than 5MB',
        photoInstruction5: 'صيغة JPG أو PNG / JPG or PNG format',
        languageBtn: 'English'
    },
    en: {
        pageTitle: 'Employee Data Entry System',
        collegeLabel: 'College *',
        collegePlaceholder: 'Select College',
        nameLabel: 'Employee Name *',
        namePlaceholder: 'Enter employee name',
        uniIdLabel: 'University ID *',
        uniIdPlaceholder: 'Enter university ID',
        emailLabel: 'Email *',
        emailPlaceholder: 'Enter email',
         verificationLabel: 'Activation Type *',
         photoOption: 'Upload Photo',
         photoSubtitle: 'Upload a clear personal photo',
         passwordOption: 'Password',
         passwordSubtitle: 'Create a secure password',
         photoLabel: 'Upload Employee Photo *',
         passwordInstruction1: 'Password Instructions:',
         passwordInstruction2: 'Must be at least 6 digits',
         passwordInstruction3: 'Must not be sequential numbers',
         passwordInstruction4: 'Numbers only (0-9)',
         passwordLabel: 'Password *',
         confirmPasswordLabel: 'Confirm Password *',
        passwordPlaceholder: 'Enter password',
        submitBtn: 'Submit Data',
        successTitle: '✅ Your data has been submitted successfully',
        successText: 'Waiting for review by administration',
        photoInstruction1: 'Photo Instructions:',
        photoInstruction2: 'Photo must be clear',
        photoInstruction3: 'White or light background',
        photoInstruction4: 'File size less than 5MB',
        photoInstruction5: 'JPG or PNG format',
        languageBtn: 'العربية'
    }
};

function setupLanguageToggle() {
    const languageBtn = document.getElementById('language-toggle');
    if (languageBtn) {
        languageBtn.addEventListener('click', toggleLanguage);
    }
}

function toggleLanguage() {
    isEnglish = !isEnglish;
    const lang = isEnglish ? 'en' : 'ar';
    const t = translations[lang];
    
    // Update all text elements
    const elements = {
        'page-title': t.pageTitle,
        'college-label': t.collegeLabel,
        'name-label': t.nameLabel,
        'uni-id-label': t.uniIdLabel,
        'email-label': t.emailLabel,
         'verification-label': t.verificationLabel,
         'photo-option': t.photoOption,
         'photo-subtitle': t.photoSubtitle,
         'password-option': t.passwordOption,
         'password-subtitle': t.passwordSubtitle,
         'photo-label': t.photoLabel,
         'password-instruction-1': t.passwordInstruction1,
         'password-instruction-2': t.passwordInstruction2,
         'password-instruction-3': t.passwordInstruction3,
         'password-instruction-4': t.passwordInstruction4,
         'password-label': t.passwordLabel,
         'confirm-password-label': t.confirmPasswordLabel,
        'submit-btn': t.submitBtn,
        'success-title': t.successTitle,
        'success-text': t.successText,
        'language-toggle': t.languageBtn
    };
    
    Object.keys(elements).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = elements[id];
        }
    });
    
    // Update placeholders
    const placeholders = {
        'name': t.namePlaceholder,
        'uni_id': t.uniIdPlaceholder,
        'email': t.emailPlaceholder,
        'password': t.passwordPlaceholder
    };
    
    Object.keys(placeholders).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.placeholder = placeholders[id];
        }
    });
    
    // Update college dropdown based on language
function updateCollegeDropdown() {
    const collegeSelect = document.getElementById('college');
    const selectedValue = collegeSelect.value;
    const colleges = db.getColleges();
    
    collegeSelect.innerHTML = isEnglish ? 
        '<option value="">Select College</option>' : 
        '<option value="">اختر الكلية</option>';
    
    colleges.forEach(college => {
        const option = document.createElement('option');
        option.value = college.id;
        option.textContent = isEnglish ? college.name_en : college.name_ar;
        collegeSelect.appendChild(option);
    });
    
    // استعادة القيمة المحددة مسبقاً
    if (selectedValue) {
        collegeSelect.value = selectedValue;
    }
}

updateCollegeDropdown();
    
    // Update page direction
    document.body.style.direction = isEnglish ? 'ltr' : 'rtl';
}

// Enhanced verification method toggle
function setupVerificationToggle() {
    const verificationRadios = document.querySelectorAll('input[name="verification_method"]');
    verificationRadios.forEach(radio => {
        radio.addEventListener('change', toggleVerificationMethod);
    });
}

// إعداد مستمعي الأحداث / Setup Event Listeners
function setupEventListeners() {
    // نموذج إدخال الموظف / Employee form
    setupFormSubmission();
    
    // تغيير طريقة التحقق / Verification method change
    const verificationRadios = document.querySelectorAll('input[name="verification_method"]');
    verificationRadios.forEach(radio => {
        radio.addEventListener('change', toggleVerificationMethod);
    });
    
    // تشغيل دالة التبديل عند التحميل
    toggleVerificationMethod();
    
    // رفع الصورة / Photo upload
    const photoInput = document.getElementById('photo');
    if (photoInput) {
        photoInput.addEventListener('change', handlePhotoUpload);
    }
    
    // إعداد مستمعي الأحداث للحقول
    setupFieldValidation();
}

// تحميل الكليات في القائمة المنسدلة
function loadColleges() {
    const collegeSelect = document.getElementById('college');
    const colleges = db.getColleges();
    
    collegeSelect.innerHTML = isEnglish ? 
        '<option value="">Select College</option>' : 
        '<option value="">اختر الكلية</option>';
    
    colleges.forEach(college => {
        const option = document.createElement('option');
        option.value = college.id;
        option.textContent = isEnglish ? college.name_en : college.name_ar;
        collegeSelect.appendChild(option);
    });
}

// تحديث قائمة الكليات بناءً على اللغة المختارة
function updateCollegeDropdown() {
    const collegeSelect = document.getElementById('college');
    const colleges = db.getColleges();
    const currentValue = collegeSelect.value; // حفظ القيمة المختارة حالياً
    
    // تحديث النص الافتراضي
    const defaultText = isEnglish ? 'Select College' : 'اختر الكلية';
    collegeSelect.innerHTML = `<option value="">${defaultText}</option>`;
    
    // إضافة الكليات بالاسم المناسب للغة
    colleges.forEach(college => {
        const option = document.createElement('option');
        option.value = college.id;
        option.textContent = isEnglish ? college.name_en : college.name_ar;
        collegeSelect.appendChild(option);
    });
    
    // استعادة القيمة المختارة إذا كانت موجودة
    if (currentValue) {
        collegeSelect.value = currentValue;
    }
}

// تبديل طريقة التحقق / Toggle Verification Method
function toggleVerificationMethod() {
    const photoChoice = document.querySelector('input[name="verification_method"][value="photo"]');
    const passwordChoice = document.querySelector('input[name="verification_method"][value="password"]');
    const photoSection = document.getElementById('photo-section');
    const passwordSection = document.getElementById('password-section');
    
    if (photoChoice && photoChoice.checked) {
        if (photoSection) photoSection.style.display = 'block';
        if (passwordSection) passwordSection.style.display = 'none';
        
        // جعل الصورة مطلوبة / Make photo required
        const photoInput = document.getElementById('photo');
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm-password');
        if (photoInput) photoInput.required = true;
        if (passwordInput) passwordInput.required = false;
        if (confirmPasswordInput) confirmPasswordInput.required = false;
    } else if (passwordChoice && passwordChoice.checked) {
        if (photoSection) photoSection.style.display = 'none';
        if (passwordSection) passwordSection.style.display = 'block';
        
        // جعل الرقم السري مطلوب / Make password required
        const photoInput = document.getElementById('photo');
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm-password');
        if (photoInput) photoInput.required = false;
        if (passwordInput) passwordInput.required = true;
        if (confirmPasswordInput) confirmPasswordInput.required = true;
    }
}

// معالجة رفع الصورة / Handle Photo Upload
function handlePhotoUpload(event) {
    const file = event.target.files[0];
    
    if (file) {
        // التحقق من نوع الملف / Check file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
        if (!allowedTypes.includes(file.type)) {
            alert('يجب أن تكون الصورة من نوع JPG أو PNG / Photo must be JPG or PNG format');
            event.target.value = '';
            return;
        }
        
        // التحقق من حجم الملف (5 ميجابايت) / Check file size (5MB)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            alert('حجم الصورة يجب أن يكون أقل من 5 ميجابايت / Photo size must be less than 5MB');
            event.target.value = '';
            return;
        }
        
        // تحويل الصورة إلى base64 / Convert image to base64
        const reader = new FileReader();
        reader.onload = function(e) {
            // حفظ الصورة في متغير عام / Save image in global variable
            window.selectedPhoto = e.target.result;
            console.log('تم اختيار الصورة بنجاح / Photo selected successfully:', file.name);
        };
        reader.readAsDataURL(file);
    }
}

// معالجة إرسال النموذج
function setupFormSubmission() {
    const form = document.getElementById('employeeForm');
    
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
}

function handleFormSubmit(event) {
    event.preventDefault();
    
    const formData = collectFormData();
    
    if (validateFormData(formData)) {
        const duplicateErrors = db.checkDuplicateEmployee(formData);
        if (duplicateErrors.length > 0) {
            const message = isEnglish ? 
                'Employee with same University ID or Email already exists' : 
                'موظف بنفس الرقم الجامعي أو الإيميل موجود مسبقاً';
            alert(message);
            return;
        }
        
        db.addEmployee(formData);
        showSuccessMessage();
        // Don't reset form immediately - let user see the success message
    }
}

// جمع البيانات من النموذج / Collect Form Data
function collectFormData() {
    const verificationMethodElement = document.querySelector('input[name="verification_method"]:checked');
    const verificationMethod = verificationMethodElement ? verificationMethodElement.value : 'password';
    
    const formData = {
        college_id: document.getElementById('college').value,
        name: document.getElementById('name').value.trim(),
        uni_id: document.getElementById('uni_id').value.trim(),
        email: document.getElementById('email').value.trim(),
        verification_method: verificationMethod,
        status: 'pending',
        submitted_at: new Date().toISOString()
    };
    
    if (verificationMethod === 'photo') {
        const photoFile = document.getElementById('photo').files[0];
        if (photoFile) {
            formData.photo_path = `uploads/${Date.now()}_${photoFile.name}`;
            formData.photo = {
                name: photoFile.name,
                size: photoFile.size,
                type: photoFile.type
            };
            formData.photo_data = window.selectedPhoto || null;
        }
    } else if (verificationMethod === 'password') {
        formData.password = document.getElementById('password').value;
    }
    
    return formData;
}

// إعادة تعيين النموذج / Reset Form
function resetForm() {
    const form = document.getElementById('employeeForm');
    if (form) {
        form.reset();
        form.style.display = 'block';
    }
    
    const successMessage = document.getElementById('successMessage');
    if (successMessage) {
        successMessage.style.display = 'none';
    }
    
    // Reset verification method to photo
    const photoRadio = document.querySelector('input[name="verification_method"][value="photo"]');
    if (photoRadio) {
        photoRadio.checked = true;
        toggleVerificationMethod();
    }
}

// دالة لإظهار رسالة النجاح / Function to show success message
function showSuccessMessage() {
    const successDiv = document.getElementById('successMessage');
    const formDiv = document.querySelector('.employee-form') || document.getElementById('employeeForm');
    
    if (successDiv) {
        // Update success message text based on current language
        const successTitle = document.getElementById('success-title');
        const successText = document.getElementById('success-text');
        
        if (successTitle) {
            successTitle.textContent = isEnglish ? translations.en.successTitle : translations.ar.successTitle;
        }
        
        if (successText) {
            successText.textContent = isEnglish ? translations.en.successText : translations.ar.successText;
        }
        
        // Add a button to add another employee if it doesn't exist
        let addAnotherBtn = successDiv.querySelector('.add-another-btn');
        if (!addAnotherBtn) {
            addAnotherBtn = document.createElement('button');
            addAnotherBtn.className = 'add-another-btn submit-btn';
            addAnotherBtn.style.marginTop = '20px';
            addAnotherBtn.onclick = function() {
                resetForm();
                successDiv.style.display = 'none';
                if (formDiv) formDiv.style.display = 'block';
            };
            successDiv.appendChild(addAnotherBtn);
        }
        
        addAnotherBtn.textContent = isEnglish ? 'Add Another Employee' : 'إضافة موظف آخر';
        
        successDiv.style.display = 'block';
        successDiv.scrollIntoView({ behavior: 'smooth' });
    }
    
    if (formDiv) {
        formDiv.style.display = 'none';
    }
}

// دالة التحقق من الرقم السري
function validatePassword(password) {
    // التحقق من الطول (6 أرقام على الأقل)
    if (password.length < 6) {
        return false;
    }
    
    // التحقق من أنه أرقام فقط
    if (!/^\d+$/.test(password)) {
        return false;
    }
    
    // التحقق من عدم وجود أرقام متسلسلة
    for (let i = 0; i < password.length - 2; i++) {
        const num1 = parseInt(password[i]);
        const num2 = parseInt(password[i + 1]);
        const num3 = parseInt(password[i + 2]);
        
        // تحقق من التسلسل الصاعد أو النازل
        if ((num2 === num1 + 1 && num3 === num2 + 1) || 
            (num2 === num1 - 1 && num3 === num2 - 1)) {
            return false;
        }
    }
    
    return true;
}

// دالة للتحقق من صحة البيانات المحسنة / Enhanced validation function
function validateFormData(data) {
    const requiredFields = ['college_id', 'name', 'uni_id'];
    
    for (let field of requiredFields) {
        if (!data[field]) {
            const message = isEnglish ? 
                'Please fill all required fields' : 
                'يرجى ملء جميع الحقول المطلوبة';
            alert(message);
            return false;
        }
    }
    
    // Validate email format only if email is provided
    if (data.email && data.email.trim() !== '') {
        if (!isValidEmail(data.email)) {
            const message = isEnglish ? 
                'Please enter a valid email' : 
                'يرجى إدخال إيميل صحيح';
            alert(message);
            return false;
        }
        
        // Check if email contains only English characters
        if (!/^[a-zA-Z0-9@._-]+$/.test(data.email)) {
            const message = isEnglish ? 
                'Email must contain only English characters' : 
                'الإيميل يجب أن يحتوي على أحرف إنجليزية فقط';
            alert(message);
            return false;
        }
    }
    
    // Validate verification method
    if (data.verification_method === 'photo') {
        const photoFile = document.getElementById('photo').files[0];
        if (!photoFile) {
            const message = isEnglish ? 
                'Please upload a photo' : 
                'يرجى رفع صورة';
            alert(message);
            return false;
        }
        
        // Validate photo size (5MB max)
        if (photoFile.size > 5 * 1024 * 1024) {
            const message = isEnglish ? 
                'Photo size must be less than 5MB' : 
                'حجم الصورة يجب أن يكون أقل من 5 ميجابايت';
            alert(message);
            return false;
        }
        
        // Validate photo type
        if (!photoFile.type.startsWith('image/')) {
            const message = isEnglish ? 
                'Please upload a valid image file' : 
                'يرجى رفع ملف صورة صحيح';
            alert(message);
            return false;
        }
    } else if (data.verification_method === 'password') {
        if (!data.password) {
            const message = isEnglish ? 
                'Please enter a password' : 
                'يرجى إدخال رقم سري';
            alert(message);
            return false;
        }
        
        const confirmPassword = document.getElementById('confirm-password').value;
        if (!confirmPassword) {
            const message = isEnglish ? 
                'Please confirm password' : 
                'يرجى تأكيد الرقم السري';
            alert(message);
            return false;
        }
        
        if (data.password !== confirmPassword) {
            const message = isEnglish ? 
                'Password and confirmation do not match' : 
                'الرقم السري وتأكيده غير متطابقين';
            alert(message);
            return false;
        }
        
        if (!validatePassword(data.password)) {
            const message = isEnglish ? 
                'Password must be at least 6 digits, numbers only, and not sequential' : 
                'الرقم السري يجب أن يكون 6 أرقام على الأقل، أرقام فقط، وبدون تسلسل';
            alert(message);
            return false;
        }
    }
    
    return true;
}

// دالة مساعدة لتنسيق التاريخ / Helper function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-SA') + ' ' + date.toLocaleTimeString('ar-SA');
}

// دالة مساعدة للتحقق من صحة الإيميل / Helper function to validate email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// دالة مساعدة لتنظيف النص / Helper function to sanitize text
function sanitizeText(text) {
    return text.trim().replace(/[<>"'&]/g, '');
}

// إضافة مستمع لإعادة تحميل الصفحة / Add listener for page reload
window.addEventListener('beforeunload', function(event) {
    const form = document.getElementById('employeeForm');
    const formData = new FormData(form);
    let hasData = false;
    
    // التحقق من وجود بيانات في النموذج / Check if form has data
    for (let [key, value] of formData.entries()) {
        if (value && value.trim() !== '') {
            hasData = true;
            break;
        }
    }
    
    // تحذير المستخدم إذا كان هناك بيانات غير محفوظة / Warn user if there's unsaved data
    if (hasData && document.getElementById('employeeForm').style.display !== 'none') {
        event.preventDefault();
        event.returnValue = 'لديك بيانات غير محفوظة. هل تريد المغادرة؟ / You have unsaved data. Do you want to leave?';
        return event.returnValue;
    }
});

// دالة لإظهار رسالة تحميل / Function to show loading message
function showLoading(show = true) {
    const submitBtn = document.querySelector('.submit-btn');
    if (show) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'جاري الإرسال... / Submitting...';
    } else {
        submitBtn.disabled = false;
        submitBtn.textContent = 'إرسال البيانات / Submit Data';
    }
}

// دالة لإظهار الأخطاء / Function to show errors
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
        background: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        border: 1px solid #f5c6cb;
    `;
    errorDiv.textContent = message;
    
    const form = document.getElementById('employeeForm');
    form.insertBefore(errorDiv, form.firstChild);
    
    // إزالة الرسالة بعد 5 ثوان / Remove message after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

// دالة لإعداد التحقق من الحقول / Function to setup field validation
function setupFieldValidation() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm-password');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const uniIdInput = document.getElementById('uni_id');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function(e) {
            // منع كتابة الأحرف وقبول الأرقام فقط / Prevent letters and accept only numbers
            const value = e.target.value;
            const numbersOnly = value.replace(/[^0-9]/g, '');
            
            if (value !== numbersOnly) {
                e.target.value = numbersOnly;
                const message = getCurrentLanguage() === 'ar' ? 
                    'يُسمح بالأرقام فقط في حقل الرقم السري' :
                    'Only numbers are allowed in password field';
                showFieldError(e.target, message);
            }
        });
        
        passwordInput.addEventListener('keypress', function(e) {
            // منع كتابة أي شيء غير الأرقام / Prevent typing anything other than numbers
            if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'Tab', 'Enter'].includes(e.key)) {
                e.preventDefault();
                const message = getCurrentLanguage() === 'ar' ? 
                    'الأرقام فقط مسموحة' :
                    'Only numbers are allowed';
                showFieldError(e.target, message);
            }
        });
    }
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function(e) {
            // منع كتابة الأحرف وقبول الأرقام فقط / Prevent letters and accept only numbers
            const value = e.target.value;
            const numbersOnly = value.replace(/[^0-9]/g, '');
            
            if (value !== numbersOnly) {
                e.target.value = numbersOnly;
                const message = getCurrentLanguage() === 'ar' ? 
                    'يُسمح بالأرقام فقط في حقل الرقم السري' :
                    'Only numbers are allowed in password field';
                showFieldError(e.target, message);
            }
        });
        
        confirmPasswordInput.addEventListener('keypress', function(e) {
            // منع كتابة أي شيء غير الأرقام / Prevent typing anything other than numbers
            if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'Tab', 'Enter'].includes(e.key)) {
                e.preventDefault();
                const message = getCurrentLanguage() === 'ar' ? 
                    'الأرقام فقط مسموحة' :
                    'Only numbers are allowed';
                showFieldError(e.target, message);
            }
        });
    }
    
    if (nameInput) {
        nameInput.addEventListener('input', function(e) {
            validateNameLanguage(e.target);
        });
        
        nameInput.addEventListener('keypress', function(e) {
            const currentLang = getCurrentLanguage();
            const char = e.key;
            
            // تجاهل المفاتيح الخاصة / Ignore special keys
            if (['Backspace', 'Delete', 'Tab', 'Enter', ' '].includes(char)) {
                return;
            }
            
            const isArabic = /[\u0600-\u06FF]/.test(char);
            const isEnglish = /[a-zA-Z]/.test(char);
            
            if (currentLang === 'ar' && isEnglish) {
                e.preventDefault();
                showFieldError(e.target, 'يرجى الكتابة باللغة العربية فقط');
            } else if (currentLang === 'en' && isArabic) {
                e.preventDefault();
                showFieldError(e.target, 'Please write in English only');
            }
        });
    }
    
    if (emailInput) {
        emailInput.addEventListener('input', function(e) {
            validateEmailFormat(e.target);
        });
    }
    
    if (uniIdInput) {
        uniIdInput.addEventListener('input', function(e) {
            // منع كتابة الأحرف وقبول الأرقام فقط / Prevent letters and accept only numbers
            const value = e.target.value;
            const numbersOnly = value.replace(/[^0-9]/g, '');
            
            if (value !== numbersOnly) {
                e.target.value = numbersOnly;
                const message = getCurrentLanguage() === 'ar' ? 
                    'يُسمح بالأرقام فقط في حقل الرقم الجامعي' :
                    'Only numbers are allowed in University ID field';
                showFieldError(e.target, message);
            }
        });
        
        uniIdInput.addEventListener('keypress', function(e) {
            // منع كتابة أي شيء غير الأرقام / Prevent typing anything other than numbers
            if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'Tab', 'Enter', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
                const message = getCurrentLanguage() === 'ar' ? 
                    'الأرقام فقط مسموحة في الرقم الجامعي' :
                    'Only numbers are allowed in University ID';
                showFieldError(e.target, message);
            }
        });
    }
}

// دالة للتحقق من لغة الاسم / Function to validate name language
function validateNameLanguage(nameField) {
    const value = nameField.value;
    const currentLang = getCurrentLanguage();
    
    if (!value) return;
    
    const hasArabic = /[\u0600-\u06FF]/.test(value);
    const hasEnglish = /[a-zA-Z]/.test(value);
    
    if (currentLang === 'ar' && hasEnglish) {
        // إزالة الأحرف الإنجليزية / Remove English characters
        const arabicOnly = value.replace(/[a-zA-Z]/g, '');
        nameField.value = arabicOnly;
        showFieldError(nameField, 'يرجى الكتابة باللغة العربية فقط');
    } else if (currentLang === 'en' && hasArabic) {
        // إزالة الأحرف العربية / Remove Arabic characters
        const englishOnly = value.replace(/[\u0600-\u06FF]/g, '');
        nameField.value = englishOnly;
        showFieldError(nameField, 'Please write in English only');
    }
}

// دالة للتحقق من تنسيق الإيميل / Function to validate email format
function validateEmailFormat(emailField) {
    const value = emailField.value;
    
    if (!value) return;
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (value && !emailRegex.test(value)) {
        const message = getCurrentLanguage() === 'ar' ? 
            'يرجى إدخال إيميل صحيح (مثال: user@example.com)' :
            'Please enter a valid email (example: user@example.com)';
        showFieldError(emailField, message);
    } else if (value && !/^[a-zA-Z0-9@._-]+$/.test(value)) {
        const message = getCurrentLanguage() === 'ar' ? 
            'الإيميل يجب أن يحتوي على أحرف إنجليزية فقط' :
            'Email must contain only English characters';
        showFieldError(emailField, message);
    }
}

// دالة لإظهار رسالة خطأ للحقل / Function to show field error message
function showFieldError(field, message) {
    // إزالة أي رسالة خطأ سابقة / Remove any previous error message
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // إنشاء رسالة خطأ جديدة / Create new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.style.cssText = `
        color: #dc3545;
        font-size: 12px;
        margin-top: 5px;
        padding: 5px;
        background: #f8d7da;
        border-radius: 3px;
        border: 1px solid #f5c6cb;
        animation: fadeIn 0.3s ease;
    `;
    errorDiv.textContent = message;
    
    // إدراج الرسالة بعد الحقل / Insert message after field
    field.parentNode.insertBefore(errorDiv, field.nextSibling);
    
    // إزالة الرسالة بعد 3 ثوان / Remove message after 3 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 300);
        }
    }, 3000);
}

console.log('تم تحميل ملف JavaScript لصفحة إدخال الموظف / Employee entry page JavaScript loaded');