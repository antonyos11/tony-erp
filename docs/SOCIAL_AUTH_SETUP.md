# 🔐 دليل إعداد تسجيل الدخول الاجتماعي للمتجر الإلكتروني

## 📋 نظرة عامة

يدعم المتجر الإلكتروني تسجيل دخول العملاء عبر الحسابات الاجتماعية التالية:
- ✅ Google
- ✅ Facebook  
- ✅ Twitter / X
- ✅ Apple
- ✅ GitHub
- ✅ Microsoft

---

## 🚀 البدء السريع

### 1. تشغيل سكريبت الإعداد

```bash
cd app
python setup_social_auth.py
```

هذا سينشئ إعدادات افتراضية لجميع المزودين (معطلين افتراضياً).

### 2. الحصول على بيانات OAuth

ستحتاج للحصول على `Client ID` و `Client Secret` من كل منصة تريد تفعيلها.

---

## 🔵 إعداد Google

1. اذهب إلى [Google Cloud Console](https://console.developers.google.com/)
2. أنشئ مشروع جديد أو اختر مشروع موجود
3. اذهب إلى **APIs & Services > Credentials**
4. اضغط **Create Credentials > OAuth Client ID**
5. اختر **Web application**
6. أضف **Authorized redirect URIs**:
   ```
   https://your-domain.com/store/auth/google/callback/
   http://localhost:8000/store/auth/google/callback/  (للتطوير)
   ```
7. احفظ **Client ID** و **Client Secret**

### الصلاحيات المطلوبة (Scopes):
```
openid email profile
```

---

## 🔵 إعداد Facebook

1. اذهب إلى [Facebook Developers](https://developers.facebook.com/)
2. أنشئ تطبيق جديد (اختر **Consumer**)
3. اذهب إلى **Settings > Basic**
4. احفظ **App ID** و **App Secret**
5. اذهب إلى **Facebook Login > Settings**
6. أضف **Valid OAuth Redirect URIs**:
   ```
   https://your-domain.com/store/auth/facebook/callback/
   ```

### الصلاحيات المطلوبة:
```
email public_profile
```

---

## 🔵 إعداد Twitter / X

1. اذهب إلى [Twitter Developer Portal](https://developer.twitter.com/)
2. أنشئ مشروع وتطبيق جديد
3. اذهب إلى **User authentication settings**
4. فعّل **OAuth 2.0**
5. أضف **Callback URL**:
   ```
   https://your-domain.com/store/auth/twitter/callback/
   ```
6. احفظ **Client ID** و **Client Secret**

### الصلاحيات المطلوبة:
```
users.read tweet.read
```

---

## 🔵 إعداد Apple

1. اذهب إلى [Apple Developer](https://developer.apple.com/)
2. اذهب إلى **Certificates, IDs & Profiles**
3. أنشئ **App ID** مع تفعيل **Sign in with Apple**
4. أنشئ **Service ID** للويب
5. أضف **Return URLs**:
   ```
   https://your-domain.com/store/auth/apple/callback/
   ```

### ملاحظة:
Apple يتطلب إعدادات إضافية معقدة. راجع [وثائق Apple](https://developer.apple.com/sign-in-with-apple/)

---

## 🔵 إعداد GitHub

1. اذهب إلى [GitHub Developer Settings](https://github.com/settings/developers)
2. اضغط **New OAuth App**
3. املأ البيانات:
   - **Application name**: اسم متجرك
   - **Homepage URL**: `https://your-domain.com`
   - **Authorization callback URL**: 
     ```
     https://your-domain.com/store/auth/github/callback/
     ```
4. احفظ **Client ID** و **Client Secret**

### الصلاحيات المطلوبة:
```
read:user user:email
```

---

## 🔵 إعداد Microsoft

1. اذهب إلى [Azure Portal](https://portal.azure.com/)
2. اذهب إلى **Azure Active Directory > App registrations**
3. أنشئ تسجيل جديد
4. أضف **Redirect URI**:
   ```
   https://your-domain.com/store/auth/microsoft/callback/
   ```
5. اذهب إلى **Certificates & secrets** لإنشاء Secret جديد
6. احفظ **Application (client) ID** و **Client Secret**

### الصلاحيات المطلوبة:
```
openid email profile User.Read
```

---

## ⚙️ إضافة البيانات في لوحة التحكم

### من لوحة تحكم المتجر:

1. سجل دخولك كمدير
2. اذهب إلى: `/store/admin/social-auth/`
3. اضغط على **تعديل** للمزود الذي تريد تفعيله
4. أضف **Client ID** و **Client Secret**
5. فعّل المزود
6. احفظ التغييرات

### أو من Admin Django:

1. اذهب إلى: `/admin/ecommerce/socialauthprovider/`
2. عدّل المزود المطلوب

---

## 🔗 روابط Callback

استخدم هذه الروابط في إعدادات OAuth لكل منصة:

| المزود | Callback URL |
|--------|--------------|
| Google | `/store/auth/google/callback/` |
| Facebook | `/store/auth/facebook/callback/` |
| Twitter | `/store/auth/twitter/callback/` |
| Apple | `/store/auth/apple/callback/` |
| GitHub | `/store/auth/github/callback/` |
| Microsoft | `/store/auth/microsoft/callback/` |

**مثال كامل:**
```
https://your-domain.com/store/auth/google/callback/
```

---

## 📱 تجربة العميل

### صفحة تسجيل الدخول:
العملاء سيرون أزرار تسجيل الدخول الاجتماعي في:
- `/store/login/` - تسجيل الدخول
- `/store/register/` - إنشاء حساب جديد

### ماذا يحدث عند التسجيل عبر حساب اجتماعي:

1. ✅ يتم إنشاء حساب مستخدم جديد
2. ✅ يتم إنشاء ملف عميل في المتجر الإلكتروني
3. ✅ يتم إنشاء سجل عميل في نظام المبيعات (partners)
4. ✅ يتم ربط الحساب الاجتماعي بالعميل
5. ✅ يستطيع العميل تسجيل الدخول مباشرة في المرات القادمة

### ربط حساب اجتماعي إضافي:
العميل يستطيع ربط أكثر من حساب اجتماعي من:
`/store/account/`

---

## 🔒 الأمان

### نصائح مهمة:

1. **لا تشارك Client Secret أبداً**
2. استخدم **HTTPS** دائماً في الإنتاج
3. قيّد **Redirect URIs** لنطاقك فقط
4. راجع الصلاحيات (Scopes) واطلب الحد الأدنى فقط
5. احفظ البيانات السرية في متغيرات البيئة `.env`

### إعداد عبر متغيرات البيئة:

```env
# Google
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Facebook
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

---

## 🔧 استكشاف الأخطاء

### "redirect_uri_mismatch":
- تأكد أن Callback URL في إعدادات المنصة يطابق تماماً ما في النظام
- تحقق من وجود `/` في نهاية الرابط

### "invalid_client":
- تأكد من صحة Client ID و Client Secret
- تأكد أن التطبيق مفعّل في المنصة

### "access_denied":
- المستخدم رفض الإذن
- تحقق من الصلاحيات المطلوبة

---

## 📊 متابعة الإحصائيات

### من لوحة التحكم:
- عدد العملاء المسجلين عبر كل منصة
- الحسابات الاجتماعية المرتبطة

### من قاعدة البيانات:
```python
from ecommerce.models import SocialAccount

# عدد التسجيلات لكل منصة
SocialAccount.objects.values('provider').annotate(count=Count('id'))
```

---

## 🆘 الدعم

إذا واجهت مشاكل:
1. راجع سجلات Django للأخطاء
2. تأكد من صحة إعدادات OAuth
3. تحقق من حالة المزود من `/store/admin/social-auth/`

---

**آخر تحديث:** ديسمبر 2025
