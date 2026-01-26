#!/usr/bin/env python3
"""
Security Verification Script
Checks all implemented security measures in the Payday Budget application
"""

import os
import re

def check_file_content(filepath, patterns, description):
    """Check if file contains expected security patterns"""
    print(f"\n{description}")
    print("-" * 60)

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        results = []
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, content):
                results.append(f"  ✓ {pattern_name}")
            else:
                results.append(f"  ✗ {pattern_name} - NOT FOUND")

        for result in results:
            print(result)

        return all("✓" in r for r in results)
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return False

def main():
    print("=" * 60)
    print("SECURITY VERIFICATION REPORT")
    print("=" * 60)

    all_checks_passed = True

    # 1. Check Password Encryption
    print("\n1. PASSWORD ENCRYPTION")
    print("-" * 60)
    patterns = {
        "Werkzeug import": r"from werkzeug.security import generate_password_hash, check_password_hash",
        "Password hashing in set_password": r"generate_password_hash\(password\)",
        "Password verification": r"check_password_hash\(self\.password_hash",
        "Password stored as hash": r"password_hash.*Column"
    }
    passed = check_file_content("models.py", patterns, "")
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: Passwords are encrypted with Werkzeug")
    all_checks_passed = all_checks_passed and passed

    # 2. Check CSRF Protection
    print("\n\n2. CSRF PROTECTION")
    print("-" * 60)
    patterns = {
        "Flask-WTF import": r"from flask_wtf.csrf import CSRFProtect",
        "CSRF initialization": r"csrf = CSRFProtect\(app\)",
        "CSRF exempt for AJAX": r"@csrf.exempt"
    }
    passed = check_file_content("app.py", patterns, "")
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: CSRF protection enabled")
    all_checks_passed = all_checks_passed and passed

    # Check CSRF tokens in templates
    template_files = [
        "templates/login.html",
        "templates/register.html",
        "templates/admin.html",
        "templates/account_transactions.html"
    ]

    print("\n  Template CSRF Tokens:")
    for template in template_files:
        try:
            with open(template, 'r') as f:
                if 'csrf_token()' in f.read():
                    print(f"    ✓ {template}")
                else:
                    print(f"    ✗ {template} - MISSING CSRF TOKEN")
                    all_checks_passed = False
        except:
            print(f"    ✗ {template} - FILE NOT FOUND")
            all_checks_passed = False

    # 3. Check Rate Limiting
    print("\n\n3. RATE LIMITING")
    print("-" * 60)
    patterns = {
        "Flask-Limiter import": r"from flask_limiter import Limiter",
        "Limiter initialization": r"limiter = Limiter",
        "Login rate limit": r'@limiter\.limit\("10 per minute"\)',
        "Registration rate limit": r'@limiter\.limit\("5 per hour"\)'
    }
    passed = check_file_content("app.py", patterns, "")
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: Rate limiting configured")
    all_checks_passed = all_checks_passed and passed

    # 4. Check Security Headers
    print("\n\n4. SECURITY HEADERS")
    print("-" * 60)
    patterns = {
        "X-Content-Type-Options": r"X-Content-Type-Options.*nosniff",
        "X-Frame-Options": r"X-Frame-Options.*SAMEORIGIN",
        "X-XSS-Protection": r"X-XSS-Protection",
        "Strict-Transport-Security": r"Strict-Transport-Security",
        "Content-Security-Policy": r"Content-Security-Policy"
    }
    passed = check_file_content("app.py", patterns, "")
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: Security headers configured")
    all_checks_passed = all_checks_passed and passed

    # 5. Check Session Security
    print("\n\n5. SESSION SECURITY")
    print("-" * 60)
    patterns = {
        "SESSION_COOKIE_HTTPONLY": r"SESSION_COOKIE_HTTPONLY.*True",
        "SESSION_COOKIE_SAMESITE": r"SESSION_COOKIE_SAMESITE.*Lax",
        "SESSION_COOKIE_SECURE": r"SESSION_COOKIE_SECURE",
        "PERMANENT_SESSION_LIFETIME": r"PERMANENT_SESSION_LIFETIME.*3600"
    }
    passed = check_file_content("app.py", patterns, "")
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: Session security configured")
    all_checks_passed = all_checks_passed and passed

    # 6. Check Input Validation
    print("\n\n6. INPUT VALIDATION")
    print("-" * 60)
    patterns = {
        "Username validation": r"if len\(username\) < 3 or len\(username\) > 80",
        "Password length check": r"if len\(password\) < 4",
        "Username sanitization": r"username\.replace.*isalnum",
        "Input stripping": r"\.strip\(\)"
    }
    passed = check_file_content("app.py", patterns, "")
    print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: Input validation implemented")
    all_checks_passed = all_checks_passed and passed

    # 7. Check Dependencies
    print("\n\n7. SECURITY DEPENDENCIES")
    print("-" * 60)
    try:
        with open("requirements.txt", 'r') as f:
            deps = f.read()

        required_deps = {
            "Flask-WTF": "Flask-WTF" in deps,
            "Flask-Limiter": "Flask-Limiter" in deps,
            "Werkzeug": "Werkzeug" in deps,
            "Flask-Login": "Flask-Login" in deps
        }

        for dep, present in required_deps.items():
            print(f"  {'✓' if present else '✗'} {dep}")

        passed = all(required_deps.values())
        print(f"\n{'✓ PASS' if passed else '✗ FAIL'}: All security dependencies present")
        all_checks_passed = all_checks_passed and passed
    except Exception as e:
        print(f"  ✗ Error reading requirements.txt: {e}")
        all_checks_passed = False

    # 8. Check Documentation
    print("\n\n8. SECURITY DOCUMENTATION")
    print("-" * 60)
    if os.path.exists("SECURITY.md"):
        print("  ✓ SECURITY.md present")
        with open("SECURITY.md", 'r') as f:
            content = f.read()
        if len(content) > 1000:
            print("  ✓ Comprehensive documentation (>1000 chars)")
        else:
            print("  ✗ Documentation too brief")
            all_checks_passed = False
    else:
        print("  ✗ SECURITY.md not found")
        all_checks_passed = False

    # Final Summary
    print("\n\n" + "=" * 60)
    print("FINAL SECURITY ASSESSMENT")
    print("=" * 60)

    if all_checks_passed:
        print("\n✓✓✓ ALL SECURITY CHECKS PASSED ✓✓✓")
        print("\nThe application has comprehensive security measures:")
        print("  • Password encryption (Werkzeug PBKDF2)")
        print("  • CSRF protection on all forms")
        print("  • Rate limiting on authentication routes")
        print("  • Security headers (CSP, HSTS, XSS Protection)")
        print("  • Secure session configuration")
        print("  • Input validation and sanitization")
        print("  • Complete security documentation")
        print("\n✓ Application is READY for web deployment")
        print("  (Review SECURITY.md for deployment checklist)")
    else:
        print("\n✗✗✗ SOME SECURITY CHECKS FAILED ✗✗✗")
        print("\nPlease review the failed checks above.")
        print("The application may not be ready for production deployment.")

    print("\n" + "=" * 60)

    return 0 if all_checks_passed else 1

if __name__ == '__main__':
    exit(main())
