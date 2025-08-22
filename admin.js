// JavaScript للوحة التحكم الإدارية / Admin Dashboard JavaScript

// متغيرات عامة / Global Variables
let currentApplicationId = null;
let currentModal = null;
let isEnglish = false;

// تحميل الصفحة / Page Load
document.addEventListener('DOMContentLoaded', function() {
    initializeAdminPage();
    setupEventListeners();
    loadColleges();
    loadApplications();
    updateStatistics();
    setupLanguageToggle();
});

// ✅ دالة مساعدة مفقودة سابقاً: تحويل base64 إلى Blob
function b64toBlob(b64Data, contentType = '', sliceSize = 512) {
    const byteCharacters = atob(b64Data);
    const byteArrays = [];
    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
        const slice = byteCharacters.slice(offset, offset + sliceSize);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }
    return new Blob(byteArrays, { type: contentType });
}

// إعداد تبديل اللغة / Setup Language Toggle
function setupLanguageToggle() {
    const languageBtn = document.getElementById('language-toggle');
    if (languageBtn) {
        languageBtn.addEventListener('click', toggleLanguage);
    }
}

// تبديل اللغة / Toggle Language
function toggleLanguage() {
    isEnglish = !isEnglish;
    
    // تحديث اتجاه الصفحة / Update page direction
    document.body.style.direction = isEnglish ? 'ltr' : 'rtl';
    
    // إعادة تحميل الطلبات لتحديث أسماء الكليات / Reload applications to update college names
    loadApplications();
    
    // تحديث نص زر اللغة / Update language button text
    const languageBtn = document.getElementById('language-toggle');
    if (languageBtn) {
        languageBtn.textContent = isEnglish ? 'العربية' : 'English';
    }
}

// تهيئة صفحة الإدارة / Initialize Admin Page
function initializeAdminPage() {
    console.log('تم تحميل لوحة التحكم الإدارية / Admin dashboard loaded');
    
    // إخفاء النافذة المنبثقة / Hide modal
    const modal = document.getElementById('reviewModal');
    modal.style.display = 'none';
}

// إعداد مستمعي الأحداث / Setup Event Listeners
function setupEventListeners() {
    // نموذج إضافة كلية / Add college form
    const addCollegeForm = document.getElementById('addCollegeForm');
    addCollegeForm.addEventListener('submit', handleAddCollege);
    
    // تصفية الطلبات / Filter applications
    const collegeFilter = document.getElementById('collegeFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    collegeFilter.addEventListener('change', filterApplications);
    statusFilter.addEventListener('change', filterApplications);
    
    // زر حذف جميع الطلبات / Delete all applications button
    const deleteAllBtn = document.getElementById('deleteAllApplicationsBtn');
    deleteAllBtn.addEventListener('click', deleteAllApplications);
    
    // النافذة المنبثقة / Modal events
    const modal = document.getElementById('reviewModal');
    const closeBtn = modal.querySelector('.close');
    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');
    const confirmRejectBtn = document.getElementById('confirmRejectBtn');
    const cancelRejectBtn = document.getElementById('cancelRejectBtn');
    
    closeBtn.addEventListener('click', closeModal);
    approveBtn.addEventListener('click', approveApplication);
    rejectBtn.addEventListener('click', showRejectSection);
    confirmRejectBtn.addEventListener('click', rejectApplication);
    cancelRejectBtn.addEventListener('click', hideRejectSection);
    
    // إغلاق النافذة عند النقر خارجها / Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
}

// تحميل الكليات / Load Colleges
function loadColleges() {
    const colleges = db.getColleges();
    
    // تحديث قائمة الكليات / Update colleges list
    displayCollegesList(colleges);
    
    // تحديث فلتر الكليات / Update college filter
    updateCollegeFilter(colleges);
}

// عرض قائمة الكليات / Display Colleges List
function displayCollegesList(colleges) {
    const collegesContainer = document.getElementById('collegesList');
    collegesContainer.innerHTML = '';
    
    if (colleges.length === 0) {
        collegesContainer.innerHTML = '<p>لا توجد كليات مضافة / No colleges added</p>';
        return;
    }
    
    colleges.forEach(college => {
        const collegeItem = document.createElement('div');
        collegeItem.className = 'college-item';
        collegeItem.innerHTML = `
            <div class="college-info">
                <h4>${college.name_ar}</h4>
                <p>${college.name_en}</p>
            </div>
            <button class="delete-college" onclick="deleteCollege(${college.id})">
                حذف / Delete
            </button>
        `;
        collegesContainer.appendChild(collegeItem);
    });
}

// تحديث فلتر الكليات / Update College Filter
function updateCollegeFilter(colleges) {
    const collegeFilter = document.getElementById('collegeFilter');
    
    // مسح الخيارات الموجودة / Clear existing options
    collegeFilter.innerHTML = '<option value="">جميع الكليات / All Colleges</option>';
    
    // إضافة الكليات / Add colleges
    colleges.forEach(college => {
        const option = document.createElement('option');
        option.value = college.id;
        option.textContent = `${college.name_ar} / ${college.name_en}`;
        collegeFilter.appendChild(option);
    });
}

// معالجة إضافة كلية / Handle Add College
function handleAddCollege(event) {
    event.preventDefault();
    
    const nameAr = document.getElementById('collegeNameAr').value.trim();
    const nameEn = document.getElementById('collegeNameEn').value.trim();
    
    if (!nameAr || !nameEn) {
        alert('يجب إدخال اسم الكلية بالعربية والإنجليزية / Both Arabic and English names are required');
        return;
    }
    
    try {
        const newCollege = db.addCollege(nameAr, nameEn);
        
        if (newCollege) {
            // إعادة تحميل الكليات / Reload colleges
            loadColleges();
            
            // مسح النموذج / Clear form
            document.getElementById('addCollegeForm').reset();
            
            alert('تم إضافة الكلية بنجاح / College added successfully');
        }
    } catch (error) {
        console.error('خطأ في إضافة الكلية / Error adding college:', error);
        alert('حدث خطأ أثناء إضافة الكلية / Error occurred while adding college');
    }
}

// حذف كلية / Delete College
function deleteCollege(collegeId) {
    const college = db.getCollegeById(collegeId);
    
    if (!college) {
        alert('الكلية غير موجودة / College not found');
        return;
    }
    
    const confirmMessage = `هل أنت متأكد من حذف كلية "${college.name_ar}"؟\nسيتم حذف جميع الموظفين المرتبطين بها أيضاً\n\nAre you sure you want to delete "${college.name_en}"?\nAll associated employees will also be deleted`;
    
    if (confirm(confirmMessage)) {
        try {
            db.deleteCollege(collegeId);
            
            // إعادة تحميل البيانات / Reload data
            loadColleges();
            loadApplications();
            updateStatistics();
            
            alert('تم حذف الكلية بنجاح / College deleted successfully');
        } catch (error) {
            console.error('خطأ في حذف الكلية / Error deleting college:', error);
            alert('حدث خطأ أثناء حذف الكلية / Error occurred while deleting college');
        }
    }
}

// تحميل الطلبات / Load Applications
function loadApplications() {
    const applications = db.getEmployees();
    displayApplications(applications);
}

// عرض الطلبات / Display Applications
function displayApplications(applications) {
    const applicationsContainer = document.getElementById('applicationsList');
    applicationsContainer.innerHTML = '';
    
    if (applications.length === 0) {
        applicationsContainer.innerHTML = '<p>لا توجد طلبات / No applications found</p>';
        return;
    }
    
    applications.forEach(application => {
        const college = db.getCollegeById(application.college_id);
        const applicationItem = document.createElement('div');
        applicationItem.className = 'application-item';
        
        // Handle both single and bilingual name formats
        const displayName = application.name || application.name_ar || 'غير محدد / Not specified';
        const displayUniId = application.uni_id || application.uni_id_ar || 'غير محدد / Not specified';
        const displayEmail = application.email || application.email_ar || 'غير محدد / Not specified';
        
        // Build verification method display
        let verificationDisplay = '';
        if (application.verification_method === 'photo') {
            if (application.photo && typeof application.photo === 'string') {
                verificationDisplay = `📷 صورة / Photo <button class="download-photo-btn" onclick="downloadPhoto(${application.id})">⬇️ تحميل / Download</button>`;
            } else {
                verificationDisplay = '📷 صورة / Photo (غير متوفرة / Not available)';
            }
        } else {
            const passwordText = application.password || 'غير محدد / Not specified';
            verificationDisplay = `🔑 رقم سري / Password: ${passwordText}`;
        }
        
        applicationItem.innerHTML = `
            <div class="application-header">
                <h4>${displayName}</h4>
                <span class="application-status status-${application.status}">
                    ${getStatusText(application.status)}
                </span>
            </div>
            
            <div class="application-details">
                <div class="detail-item">
                    <strong>الكلية / College:</strong>
                    ${college ? (isEnglish ? college.name_en : college.name_ar) : 'غير محدد / Not specified'}
                </div>
                
                <div class="detail-item">
                    <strong>الرقم الجامعي / University ID:</strong>
                    ${displayUniId}
                </div>
                
                <div class="detail-item">
                    <strong>الإيميل / Email:</strong>
                    ${displayEmail}
                </div>
                
                <div class="detail-item">
                    <strong>طريقة التحقق / Verification:</strong>
                    ${verificationDisplay}
                </div>
                
                <div class="detail-item">
                    <strong>تاريخ التقديم / Application Date:</strong>
                    ${formatDate(application.created_at)}
                </div>
                
                ${application.notes ? `
                    <div class="detail-item">
                        <strong>الملاحظات / Notes:</strong>
                        ${application.notes}
                    </div>
                ` : ''}
            </div>
            
            <div class="application-actions">
                <button class="view-details-btn" onclick="openApplicationModal(${application.id})">
                    مراجعة الطلب / Review Application
                </button>
                <button class="delete-application-btn" onclick="deleteApplication(${application.id})">
                    🗑️ حذف / Delete
                </button>
            </div>
        `;
        
        applicationsContainer.appendChild(applicationItem);
    });
}

// تصفية الطلبات / Filter Applications
function filterApplications() {
    const collegeFilter = document.getElementById('collegeFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    
    const filters = {};
    
    if (collegeFilter) {
        filters.college_id = collegeFilter;
    }
    
    if (statusFilter) {
        filters.status = statusFilter;
    }
    
    const filteredApplications = db.searchEmployees(filters);
    displayApplications(filteredApplications);
}

// فتح نافذة مراجعة الطلب / Open Application Modal
function openApplicationModal(applicationId) {
    const application = db.getEmployeeById(applicationId);
    
    if (!application) {
        alert('الطلب غير موجود / Application not found');
        return;
    }
    
    currentApplicationId = applicationId;
    
    // ملء تفاصيل الطلب / Fill application details
    const college = db.getCollegeById(application.college_id);
    const detailsContainer = document.getElementById('applicationDetails');
    
    // Handle both single and bilingual data formats
    const displayName = application.name || application.name_ar || 'غير محدد / Not specified';
    const displayUniId = application.uni_id || application.uni_id_ar || 'غير محدد / Not specified';
    const displayEmail = application.email || application.email_ar || 'غير محدد / Not specified';
    
    // Build verification method display
    let verificationDisplay = '';
    if (application.verification_method === 'photo') {
        if (application.photo && typeof application.photo === 'string') {
            verificationDisplay = `
                <p>📷 صورة / Photo</p>
                <div class="photo-container">
                    <img src="${application.photo}" alt="Employee Photo" class="employee-photo" onclick="viewFullPhoto('${application.photo}')">
                    <div class="photo-actions">
                        <button class="download-photo-btn" onclick="downloadPhoto(${application.id})">⬇️ تحميل الصورة / Download Photo</button>
                        <button class="view-photo-btn" onclick="viewFullPhoto('${application.photo}')">🔍 عرض كامل / Full View</button>
                    </div>
                </div>
            `;
        } else {
            verificationDisplay = '<p>📷 صورة / Photo (غير متوفرة / Not available)</p>';
        }
    } else {
        const passwordText = application.password || 'غير محدد / Not specified';
        verificationDisplay = `<p>🔑 رقم سري / Password: <strong>${passwordText}</strong></p>`;
    }
    
    detailsContainer.innerHTML = `
        <div class="application-full-details">
            <div class="detail-row">
                <div class="detail-item">
                    <strong>الاسم / Name:</strong>
                    <p>${displayName}</p>
                </div>
                <div class="detail-item">
                    <strong>الحالة الحالية / Current Status:</strong>
                    <p class="status-${application.status}">${getStatusText(application.status)}</p>
                </div>
            </div>
            
            <div class="detail-row">
                <div class="detail-item">
                    <strong>الكلية / College:</strong>
                    <p>${college ? (isEnglish ? college.name_en : college.name_ar) : 'غير محدد / Not specified'}</p>
                </div>
                <div class="detail-item">
                    <strong>الرقم الجامعي / University ID:</strong>
                    <p>${displayUniId}</p>
                </div>
            </div>
            
            <div class="detail-row">
                <div class="detail-item">
                    <strong>الإيميل / Email:</strong>
                    <p>${displayEmail}</p>
                </div>
                <div class="detail-item">
                    <strong>طريقة التحقق / Verification Method:</strong>
                    ${verificationDisplay}
                </div>
            </div>
            
            <div class="detail-row">
                <div class="detail-item">
                    <strong>تاريخ التقديم / Application Date:</strong>
                    <p>${formatDate(application.created_at)}</p>
                </div>
            </div>
            
            ${application.notes ? `
                <div class="detail-item">
                    <strong>الملاحظات السابقة / Previous Notes:</strong>
                    <p class="notes-text">${application.notes}</p>
                </div>
            ` : ''}
        </div>
    `;
    
    // إظهار أو إخفاء أزرار المراجعة حسب الحالة / Show/hide review buttons based on status
    const reviewActions = document.querySelector('.review-actions');
    if (application.status === 'pending') {
        reviewActions.style.display = 'block';
    } else {
        reviewActions.style.display = 'none';
    }
    
    // إخفاء قسم الرفض / Hide reject section
    hideRejectSection();
    
    // إظهار النافذة / Show modal
    const modal = document.getElementById('reviewModal');
    modal.style.display = 'flex';
    currentModal = modal;
}

// إغلاق النافذة المنبثقة / Close Modal
function closeModal() {
    const modal = document.getElementById('reviewModal');
    modal.style.display = 'none';
    currentApplicationId = null;
    currentModal = null;
    hideRejectSection();
}

// قبول الطلب / Approve Application
function approveApplication() {
    if (!currentApplicationId) {
        alert('لم يتم تحديد طلب / No application selected');
        return;
    }
    
    if (confirm('هل أنت متأكد من قبول هذا الطلب؟ / Are you sure you want to approve this application?')) {
        try {
            const updatedEmployee = db.updateEmployeeStatus(currentApplicationId, 'approved');
            
            if (updatedEmployee) {
                alert('تم قبول الطلب بنجاح / Application approved successfully');
                closeModal();
                loadApplications();
                updateStatistics();
            }
        } catch (error) {
            console.error('خطأ في قبول الطلب / Error approving application:', error);
            alert('حدث خطأ أثناء قبول الطلب / Error occurred while approving application');
        }
    }
}

// إظهار قسم الرفض / Show Reject Section
function showRejectSection() {
    const rejectSection = document.getElementById('rejectSection');
    rejectSection.style.display = 'block';
    
    // التركيز على حقل الملاحظات / Focus on notes field
    document.getElementById('rejectNotes').focus();
}

// إخفاء قسم الرفض / Hide Reject Section
function hideRejectSection() {
    const rejectSection = document.getElementById('rejectSection');
    rejectSection.style.display = 'none';
    
    // مسح الملاحظات / Clear notes
    document.getElementById('rejectNotes').value = '';
}

// رفض الطلب / Reject Application
function rejectApplication() {
    if (!currentApplicationId) {
        alert('لم يتم تحديد طلب / No application selected');
        return;
    }
    
    const notes = document.getElementById('rejectNotes').value.trim();
    
    if (!notes) {
        alert('يجب إدخال سبب الرفض / Rejection reason is required');
        return;
    }
    
    if (confirm('هل أنت متأكد من رفض هذا الطلب؟ / Are you sure you want to reject this application?')) {
        try {
            const updatedEmployee = db.updateEmployeeStatus(currentApplicationId, 'rejected', notes);
            
            if (updatedEmployee) {
                alert('تم رفض الطلب بنجاح / Application rejected successfully');
                closeModal();
                loadApplications();
                updateStatistics();
            }
        } catch (error) {
            console.error('خطأ في رفض الطلب / Error rejecting application:', error);
            alert('حدث خطأ أثناء رفض الطلب / Error occurred while rejecting application');
        }
    }
}

// تحديث الإحصائيات / Update Statistics
function updateStatistics() {
    const stats = db.getStatistics();
    console.log('إحصائيات النظام / System Statistics:', stats);
}

// الحصول على نص الحالة / Get Status Text
function getStatusText(status) {
    switch (status) {
        case 'pending':
            return 'بانتظار المراجعة / Pending Review';
        case 'approved':
            return '✅ مقبول / Approved';
        case 'rejected':
            return '❌ مرفوض / Rejected';
        default:
            return 'غير محدد / Unknown';
    }
}

// تنسيق التاريخ / Format Date
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    return date.toLocaleDateString('ar-SA', options) + ' / ' + date.toLocaleDateString('en-US', options);
}

// تصدير البيانات / Export Data
function exportData() {
    try {
        const data = db.exportData();
        const dataStr = JSON.stringify(data, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `employee_data_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        alert('تم تصدير البيانات بنجاح / Data exported successfully');
    } catch (error) {
        console.error('خطأ في تصدير البيانات / Error exporting data:', error);
        alert('حدث خطأ أثناء تصدير البيانات / Error occurred while exporting data');
    }
}

// استيراد البيانات / Import Data
function importData(event) {
    const file = event.target.files[0];
    
    if (!file) {
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            
            if (confirm('هل أنت متأكد من استيراد البيانات؟ سيتم استبدال البيانات الحالية / Are you sure you want to import data? Current data will be replaced')) {
                db.importData(data);
                location.reload();
            }
        } catch (error) {
            console.error('خطأ في استيراد البيانات / Error importing data:', error);
            alert('ملف البيانات غير صحيح / Invalid data file');
        }
    };
    
    reader.readAsText(file);
}

// حذف طلب واحد / Delete single application
function deleteApplication(applicationId) {
    const application = db.getEmployeeById(applicationId);
    
    if (!application) {
        alert('الطلب غير موجود / Application not found');
        return;
    }
    
    const confirmMessage = `هل أنت متأكد من حذف طلب "${application.name || application.name_ar || 'غير محدد'}"؟\n\nAre you sure you want to delete the application for "${application.name || application.name_ar || 'Not specified'}"?`;
    
    if (confirm(confirmMessage)) {
        const employees = db.getEmployees();
        const updatedEmployees = employees.filter(emp => emp.id !== applicationId);
        localStorage.setItem('employees', JSON.stringify(updatedEmployees));
        
        loadApplications();
        updateStatistics();
        
        alert('تم حذف الطلب بنجاح / Application deleted successfully');
    }
}

// حذف جميع الطلبات / Delete all applications
function deleteAllApplications() {
    const employees = db.getEmployees();
    
    if (employees.length === 0) {
        alert('لا توجد طلبات للحذف / No applications to delete');
        return;
    }
    
    const confirmMessage = `هل أنت متأكد من حذف جميع الطلبات (${employees.length} طلب)؟\n\nهذا الإجراء لا يمكن التراجع عنه!\n\nAre you sure you want to delete all applications (${employees.length} applications)?\n\nThis action cannot be undone!`;
    
    if (confirm(confirmMessage)) {
        localStorage.removeItem('employees');
        loadApplications();
        updateStatistics();
        alert('تم حذف جميع الطلبات بنجاح / All applications deleted successfully');
    }
}

// Function to download photo
function downloadPhoto(applicationId) {
    const application = db.getEmployeeById(applicationId);
    
    if (!application) {
        alert('الطلب غير موجود / Application not found');
        return;
    }
    
    try {
        // التحقق من وجود الصورة وتنسيقها
        if (!application.photo || typeof application.photo !== 'string') {
            throw new Error('بيانات الصورة غير صالحة / Invalid photo data');
        }
        
        if (!application.photo.startsWith('data:image/')) {
            throw new Error('صيغة الصورة غير مدعومة / Invalid image format');
        }
        
        const [header, data] = application.photo.split(',');
        const mimeMatch = header.match(/:(.*?);/);
        
        if (!mimeMatch) {
            throw new Error('تعذر تحديد نوع الصورة / Could not determine image type');
        }
        
        const mimeType = mimeMatch[1];
        const blob = b64toBlob(data, mimeType);
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `employee_photo_${applicationId}_${Date.now()}.${mimeType.split('/')[1] || 'png'}`;
        
        document.body.appendChild(a);
        setTimeout(() => {
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);
    } catch (error) {
        console.error('خطأ في تحميل الصورة:', error);
        alert(error.message || 'حدث خطأ أثناء تحميل الصورة / Error downloading photo');
    }
}

// Function to view full photo
let photoWindow = null;

function viewFullPhoto(photoUrl) {
    if (photoWindow && !photoWindow.closed) {
        photoWindow.close();
    }
    
    photoWindow = window.open('', '_blank');
    photoWindow.document.write(`
        <html>
            <head>
                <title>عرض الصورة الكاملة / Full Photo View</title>
                <style>
                    body { margin: 0; padding: 20px; text-align: center; }
                    img { max-width: 90%; max-height: 90vh; object-fit: contain; }
                </style>
            </head>
            <body>
                <img src="${photoUrl}" onload="this.style.opacity='1'" style="opacity:0; transition: opacity 0.3s;">
            </body>
        </html>
    `);
}

// Function to close photo modal
function closePhotoModal() {
    const modal = document.querySelector('.photo-modal');
    if (modal) {
        document.body.removeChild(modal);
    }
}

console.log('تم تحميل ملف JavaScript للوحة التحكم الإدارية / Admin dashboard JavaScript loaded');
