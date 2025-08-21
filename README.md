# نظام إدارة الموظفين - Employee Management System

## وصف المشروع / Project Description

نظام إدارة الموظفين هو تطبيق ويب يتكون من صفحتين رئيسيتين:
- صفحة إدخال بيانات الموظفين
- لوحة التحكم الإدارية لمراجعة الطلبات

Employee Management System is a web application consisting of two main pages:
- Employee data entry page
- Admin dashboard for reviewing applications

## الملفات / Files

- `index.html` - صفحة إدخال الموظف / Employee entry page
- `admin.html` - لوحة التحكم الإدارية / Admin dashboard
- `styles.css` - ملف الأنماط / Styles file
- `database.js` - إدارة قاعدة البيانات / Database management
- `script.js` - JavaScript لصفحة الإدخال / Entry page JavaScript
- `admin.js` - JavaScript للوحة التحكم / Admin dashboard JavaScript

## المتطلبات / Requirements

- متصفح ويب حديث / Modern web browser
- دعم JavaScript / JavaScript support
- دعم Local Storage / Local Storage support

## كيفية التشغيل / How to Run

### الطريقة الأولى: فتح الملفات مباشرة / Method 1: Open Files Directly

1. افتح ملف `index.html` في المتصفح لصفحة إدخال الموظف
   Open `index.html` in browser for employee entry page

2. افتح ملف `admin.html` في المتصفح للوحة التحكم الإدارية
   Open `admin.html` in browser for admin dashboard

### الطريقة الثانية: استخدام خادم محلي / Method 2: Using Local Server

#### باستخدام Python / Using Python:
```bash
python -m http.server 8000
```

#### باستخدام Node.js / Using Node.js:
```bash
npx http-server -p 8000
```

#### باستخدام PHP / Using PHP:
```bash
php -S localhost:8000
```

ثم افتح المتصفح على العنوان: `http://localhost:8000`
Then open browser at: `http://localhost:8000`

## الميزات / Features

### صفحة إدخال الموظف / Employee Entry Page
- إدخال بيانات الموظف بالعربية والإنجليزية / Employee data entry in Arabic and English
- اختيار الكلية من قائمة منسدلة / College selection from dropdown
- خيار التحقق بالصورة أو الرقم السري / Verification by photo or password
- التحقق من صحة البيانات / Data validation
- التحقق من تكرار البيانات / Duplicate data checking
- رسائل النجاح والخطأ / Success and error messages

### لوحة التحكم الإدارية / Admin Dashboard
- إدارة الكليات (إضافة/حذف) / College management (add/delete)
- مراجعة طلبات الموظفين / Review employee applications
- تصفية الطلبات حسب الكلية والحالة / Filter applications by college and status
- قبول أو رفض الطلبات مع الملاحظات / Approve or reject applications with notes
- عرض تفاصيل كاملة للطلبات / Display complete application details

## قاعدة البيانات / Database

يستخدم النظام Local Storage لحفظ البيانات مع الجداول التالية:
The system uses Local Storage to save data with the following tables:

### جدول الكليات / Colleges Table
- `id` - معرف الكلية / College ID
- `name_ar` - اسم الكلية بالعربية / College name in Arabic
- `name_en` - اسم الكلية بالإنجليزية / College name in English

### جدول الموظفين / Employees Table
- `id` - معرف الموظف / Employee ID
- `college_id` - معرف الكلية / College ID
- `name_ar` - الاسم بالعربية / Name in Arabic
- `name_en` - الاسم بالإنجليزية / Name in English
- `uni_id_ar` - الرقم الجامعي بالعربية / University ID in Arabic
- `uni_id_en` - الرقم الجامعي بالإنجليزية / University ID in English
- `email_ar` - الإيميل بالعربية / Email in Arabic
- `email_en` - الإيميل بالإنجليزية / Email in English
- `photo_path` - مسار الصورة / Photo path
- `password` - الرقم السري / Password
- `verification_method` - طريقة التحقق / Verification method
- `status` - حالة الطلب / Application status
- `notes` - الملاحظات / Notes
- `created_at` - تاريخ الإنشاء / Creation date
- `updated_at` - تاريخ التحديث / Update date

## حالات الطلب / Application Status

- `pending` - بانتظار المراجعة / Pending review
- `approved` - مقبول / Approved
- `rejected` - مرفوض / Rejected

## التحقق من البيانات / Data Validation

- التحقق من وجود جميع الحقول المطلوبة / Check for all required fields
- التحقق من صيغة الإيميل / Email format validation
- التحقق من تكرار الرقم الجامعي والإيميل / Check for duplicate university ID and email
- التحقق من نوع وحجم الصورة / Photo type and size validation

## الأمان / Security

- تنظيف البيانات المدخلة / Input data sanitization
- التحقق من صحة الملفات المرفوعة / Uploaded file validation
- حماية من XSS / XSS protection

## التصميم المتجاوب / Responsive Design

- يدعم جميع أحجام الشاشات / Supports all screen sizes
- تصميم متجاوب للهواتف والأجهزة اللوحية / Responsive design for mobile and tablets
- واجهة مستخدم حديثة وجذابة / Modern and attractive user interface

## المتصفحات المدعومة / Supported Browsers

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## استكشاف الأخطاء / Troubleshooting

### مشكلة عدم حفظ البيانات / Data Not Saving Issue
- تأكد من تفعيل JavaScript / Ensure JavaScript is enabled
- تأكد من دعم Local Storage / Ensure Local Storage is supported
- امسح cache المتصفح / Clear browser cache

### مشكلة عدم ظهور الكليات / Colleges Not Showing Issue
- تحقق من console للأخطاء / Check console for errors
- تأكد من تحميل ملف database.js / Ensure database.js is loaded

## التطوير المستقبلي / Future Development

- إضافة قاعدة بيانات حقيقية / Add real database
- تطوير API للخادم / Develop server API
- إضافة نظام المصادقة / Add authentication system
- تحسين الأمان / Improve security
- إضافة التقارير والإحصائيات / Add reports and statistics

## الدعم / Support

للحصول على الدعم أو الإبلاغ عن مشاكل، يرجى التواصل مع فريق التطوير.
For support or to report issues, please contact the development team.

---

**تم تطوير هذا النظام باستخدام HTML5, CSS3, JavaScript**
**This system was developed using HTML5, CSS3, JavaScript**