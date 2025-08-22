// قاعدة البيانات المحلية / Local Database
class Database {
    constructor() {
        this.initializeDatabase();
    }

    // تهيئة قاعدة البيانات / Initialize Database
    initializeDatabase() {
        // إنشاء الجداول إذا لم تكن موجودة / Create tables if they don't exist
        if (!localStorage.getItem('colleges')) {
            const defaultColleges = [
                { id: 1, name_ar: 'كلية الهندسة', name_en: 'College of Engineering' },
                { id: 2, name_ar: 'كلية الطب', name_en: 'College of Medicine' },
                { id: 3, name_ar: 'كلية العلوم', name_en: 'College of Science' },
                { id: 4, name_ar: 'كلية الآداب', name_en: 'College of Arts' },
                { id: 5, name_ar: 'كلية إدارة الأعمال', name_en: 'College of Business Administration' }
            ];
            localStorage.setItem('colleges', JSON.stringify(defaultColleges));
        }

        if (!localStorage.getItem('employees')) {
            localStorage.setItem('employees', JSON.stringify([]));
        }

        if (!localStorage.getItem('nextCollegeId')) {
            localStorage.setItem('nextCollegeId', '6');
        }

        if (!localStorage.getItem('nextEmployeeId')) {
            localStorage.setItem('nextEmployeeId', '1');
        }
    }

    // إدارة الكليات / College Management
    getColleges() {
        return JSON.parse(localStorage.getItem('colleges') || '[]');
    }

    addCollege(nameAr, nameEn) {
        const colleges = this.getColleges();
        const nextId = parseInt(localStorage.getItem('nextCollegeId'));
        
        const newCollege = {
            id: nextId,
            name_ar: nameAr,
            name_en: nameEn
        };
        
        colleges.push(newCollege);
        localStorage.setItem('colleges', JSON.stringify(colleges));
        localStorage.setItem('nextCollegeId', (nextId + 1).toString());
        
        return newCollege;
    }

    deleteCollege(collegeId) {
        const colleges = this.getColleges();
        const filteredColleges = colleges.filter(college => college.id !== collegeId);
        localStorage.setItem('colleges', JSON.stringify(filteredColleges));
        
        // حذف الموظفين المرتبطين بهذه الكلية / Delete employees associated with this college
        const employees = this.getEmployees();
        const filteredEmployees = employees.filter(employee => employee.college_id !== collegeId);
        localStorage.setItem('employees', JSON.stringify(filteredEmployees));
        
        return true;
    }

    getCollegeById(collegeId) {
        const colleges = this.getColleges();
        return colleges.find(college => college.id === collegeId);
    }

    // إدارة الموظفين / Employee Management
    getEmployees() {
        return JSON.parse(localStorage.getItem('employees') || '[]');
    }

    addEmployee(employeeData) {
        const employees = this.getEmployees();
        const nextId = parseInt(localStorage.getItem('nextEmployeeId'));
        
        const newEmployee = {
            id: nextId,
            college_id: parseInt(employeeData.college_id),
            name: employeeData.name,
            uni_id: employeeData.uni_id,
            email: employeeData.email,
            password: employeeData.password,
            verification_method: employeeData.verification_method || 'password',
            photo: employeeData.photo || null,
            photo_path: employeeData.photo_path || null,
            status: employeeData.status || 'pending',
            notes: null,
            created_at: employeeData.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString()
        };
        
        employees.push(newEmployee);
        localStorage.setItem('employees', JSON.stringify(employees));
        localStorage.setItem('nextEmployeeId', (nextId + 1).toString());
        
        return newEmployee;
    }

    updateEmployeeStatus(employeeId, status, notes = null) {
        const employees = this.getEmployees();
        const employeeIndex = employees.findIndex(emp => emp.id === employeeId);
        
        if (employeeIndex !== -1) {
            employees[employeeIndex].status = status;
            employees[employeeIndex].notes = notes;
            employees[employeeIndex].updated_at = new Date().toISOString();
            
            localStorage.setItem('employees', JSON.stringify(employees));
            return employees[employeeIndex];
        }
        
        return null;
    }

    getEmployeeById(employeeId) {
        const employees = this.getEmployees();
        return employees.find(employee => employee.id === employeeId);
    }

    getEmployeesByCollege(collegeId) {
        const employees = this.getEmployees();
        return employees.filter(employee => employee.college_id === collegeId);
    }

    getEmployeesByStatus(status) {
        const employees = this.getEmployees();
        return employees.filter(employee => employee.status === status);
    }

    // البحث والتصفية / Search and Filter
    searchEmployees(filters = {}) {
        let employees = this.getEmployees();
        
        if (filters.college_id) {
            employees = employees.filter(emp => emp.college_id === parseInt(filters.college_id));
        }
        
        if (filters.status) {
            employees = employees.filter(emp => emp.status === filters.status);
        }
        
        if (filters.search_term) {
            const searchTerm = filters.search_term.toLowerCase();
            employees = employees.filter(emp => 
                emp.name.toLowerCase().includes(searchTerm) ||
                emp.email.toLowerCase().includes(searchTerm) ||
                emp.uni_id.includes(searchTerm)
            );
        }
        
        return employees;
    }

    // إحصائيات / Statistics
    getStatistics() {
        const employees = this.getEmployees();
        const colleges = this.getColleges();
        
        return {
            total_colleges: colleges.length,
            total_employees: employees.length,
            pending_applications: employees.filter(emp => emp.status === 'pending').length,
            approved_applications: employees.filter(emp => emp.status === 'approved').length,
            rejected_applications: employees.filter(emp => emp.status === 'rejected').length
        };
    }

    // تصدير البيانات / Export Data
    exportData() {
        return {
            colleges: this.getColleges(),
            employees: this.getEmployees(),
            exported_at: new Date().toISOString()
        };
    }

    // استيراد البيانات / Import Data
    importData(data) {
        if (data.colleges) {
            localStorage.setItem('colleges', JSON.stringify(data.colleges));
        }
        
        if (data.employees) {
            localStorage.setItem('employees', JSON.stringify(data.employees));
        }
        
        return true;
    }

    // مسح جميع البيانات / Clear All Data
    clearAllData() {
        localStorage.removeItem('colleges');
        localStorage.removeItem('employees');
        localStorage.removeItem('nextCollegeId');
        localStorage.removeItem('nextEmployeeId');
        this.initializeDatabase();
        return true;
    }

    // التحقق من صحة البيانات / Data Validation
    validateEmployeeData(data) {
        const errors = [];
        
        if (!data.college_id || data.college_id === '') {
            errors.push('يجب اختيار الكلية / College must be selected');
        }
        
        if (!data.name || data.name.trim() === '') {
            errors.push('يجب إدخال اسم الموظف / Employee name is required');
        }
        
        if (!data.uni_id || data.uni_id.trim() === '') {
            errors.push('يجب إدخال الرقم الجامعي / University ID is required');
        }
        
        // التحقق من صيغة الإيميل فقط إذا تم إدخاله / Email format validation only if provided
        if (data.email && data.email.trim() !== '') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email)) {
                errors.push('صيغة الإيميل غير صحيحة / Invalid email format');
            }
            
            // التحقق من أن الإيميل يحتوي على أحرف إنجليزية فقط / Check if email contains only English characters
            if (!/^[a-zA-Z0-9@._-]+$/.test(data.email)) {
                errors.push('الإيميل يجب أن يحتوي على أحرف إنجليزية فقط / Email must contain only English characters');
            }
        }
        
        // التحقق من طريقة التحقق / Verification method validation
        if (data.verification_method === 'photo' && !data.photo_path) {
            errors.push('يجب رفع صورة عند اختيار طريقة التحقق بالصورة / Photo is required when selecting photo verification');
        }
        
        if (data.verification_method === 'password' && (!data.password || data.password.trim() === '')) {
            errors.push('يجب إدخال الرقم السري / Password is required');
        }
        
        return errors;
    }

    // التحقق من تكرار البيانات / Check for duplicate data
    checkDuplicateEmployee(data, excludeId = null) {
        const employees = this.getEmployees();
        const duplicates = [];
        
        // التحقق من تكرار الرقم الجامعي / Check for duplicate university ID
        const duplicateUniId = employees.find(emp => 
            emp.uni_id === data.uni_id && emp.id !== excludeId
        );
        
        if (duplicateUniId) {
            duplicates.push('الرقم الجامعي مستخدم مسبقاً / University ID already exists');
        }
        
        // التحقق من تكرار الإيميل فقط إذا تم إدخاله / Check for duplicate email only if provided
        if (data.email && data.email.trim() !== '') {
            const duplicateEmail = employees.find(emp => 
                emp.email === data.email && emp.id !== excludeId
            );
            
            if (duplicateEmail) {
                duplicates.push('الإيميل مستخدم مسبقاً / Email already exists');
            }
        }
        
        return duplicates;
    }
}

// إنشاء مثيل من قاعدة البيانات / Create database instance
const db = new Database();