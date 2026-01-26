# Security Documentation

## Overview
This document outlines the security measures implemented in the Payday Budget application and best practices for secure deployment.

## Implemented Security Features

### 1. Password Security
- **Password Hashing**: All passwords are hashed using Werkzeug's `generate_password_hash()` with PBKDF2
- **No Plaintext Storage**: Passwords are never stored in plaintext
- **Minimum Length**: 4 character minimum enforced (consider increasing to 8+ for production)
- **Password Validation**: Confirmation required during registration and password changes

### 2. CSRF Protection
- **Flask-WTF CSRF**: CSRF protection enabled on all POST forms
- **Token Validation**: All form submissions require valid CSRF tokens
- **Coverage**: Login, registration, admin panel, transactions, accounts, categories, payees, budgets, transfers

### 3. Rate Limiting
- **Global Limits**: 200 requests per day, 50 requests per hour per IP
- **Login Protection**: 10 login attempts per minute per IP
- **Registration Protection**: 5 registration attempts per hour per IP
- **Brute Force Prevention**: Limits automated attacks

### 4. Session Security
- **HTTP Only Cookies**: Prevents XSS attacks from accessing session cookies
- **SameSite Protection**: Set to 'Lax' to prevent CSRF attacks
- **Secure Cookies**: Enabled when HTTPS is active
- **Session Timeout**: 1 hour automatic logout

### 5. Security Headers
All responses include the following security headers:
- **X-Content-Type-Options**: nosniff (prevents MIME sniffing)
- **X-Frame-Options**: SAMEORIGIN (prevents clickjacking)
- **X-XSS-Protection**: 1; mode=block (enables browser XSS filter)
- **Strict-Transport-Security**: Forces HTTPS for 1 year
- **Content-Security-Policy**: Restricts resource loading to trusted sources

### 6. Input Validation
- **Username Validation**: 3-80 characters, alphanumeric with underscores/hyphens only
- **Password Validation**: Minimum 4 characters (increase for production)
- **Input Sanitization**: Strips whitespace, validates lengths
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **XSS Protection**: Jinja2 auto-escapes all template variables

### 7. Admin Panel Security
- **Role-Based Access**: Admin routes protected with `@login_required` and admin checks
- **Self-Protection**: Users cannot remove their own admin privileges
- **Registration Control**: Admins can disable public registration
- **Password Management**: Admins can reset user passwords with validation

### 8. Database Security
- **ORM Usage**: SQLAlchemy ORM prevents SQL injection
- **User Isolation**: All queries filtered by `user_id`
- **No Direct SQL**: All database operations through ORM

## Deployment Security Checklist

### Before Deploying to Production

#### 1. Environment Variables
```bash
# REQUIRED: Set a strong secret key
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Enable HTTPS
export HTTPS_ENABLED="true"

# Set Flask environment
export FLASK_ENV="production"
```

#### 2. HTTPS Configuration
- [ ] Obtain SSL/TLS certificate (Let's Encrypt recommended)
- [ ] Configure web server (Nginx/Apache) to handle HTTPS
- [ ] Redirect all HTTP traffic to HTTPS
- [ ] Enable HSTS header (already configured in app)

#### 3. Database Security
- [ ] Move database outside web root
- [ ] Set proper file permissions: `chmod 600 payday_budget.db`
- [ ] Regular backups with encryption
- [ ] Consider migrating to PostgreSQL for production

#### 4. Server Configuration
- [ ] Use a production WSGI server (Gunicorn, uWSGI)
- [ ] Run behind a reverse proxy (Nginx, Apache)
- [ ] Configure firewall (allow only 80, 443)
- [ ] Keep server and packages updated
- [ ] Disable debug mode (already disabled)

#### 5. Application Configuration
- [ ] Increase minimum password length to 8+ characters
- [ ] Review and adjust rate limits based on usage
- [ ] Enable logging for security events
- [ ] Set up monitoring and alerts
- [ ] Configure automated backups

#### 6. Additional Hardening
- [ ] Use fail2ban to block repeated failed logins
- [ ] Implement 2FA for admin accounts (future enhancement)
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Monitor for vulnerabilities

## Example Production Deployment

### Using Gunicorn + Nginx

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install gunicorn
```

#### 2. Create Gunicorn Service
```bash
# /etc/systemd/system/payday-budget.service
[Unit]
Description=Payday Budget Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/Payday-Budget
Environment="SECRET_KEY=your-secret-key-here"
Environment="HTTPS_ENABLED=true"
ExecStart=/usr/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

#### 3. Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/Payday-Budget/static;
    }
}
```

## Security Incident Response

### If You Suspect a Breach:
1. Immediately change all admin passwords
2. Review application logs for suspicious activity
3. Check database for unauthorized modifications
4. Revoke all active sessions
5. Update SECRET_KEY (forces all users to re-login)
6. Review and patch vulnerabilities
7. Notify affected users if data was compromised

## Regular Maintenance

### Weekly:
- Review application logs
- Check for failed login attempts
- Monitor disk space and performance

### Monthly:
- Update dependencies: `pip install -U -r requirements.txt`
- Review security advisories
- Test backup restoration
- Check SSL certificate expiration

### Quarterly:
- Security audit
- Password policy review
- Update documentation

## Known Limitations

1. **Rate Limiting Storage**: Currently uses in-memory storage (resets on restart)
   - **Solution**: Use Redis for production: `storage_uri="redis://localhost:6379"`

2. **Session Storage**: Uses Flask's default cookie-based sessions
   - **Solution**: Consider server-side sessions for sensitive data

3. **Password Strength**: Minimum 4 characters is weak
   - **Recommendation**: Increase to 12+ characters in production

4. **No 2FA**: Two-factor authentication not implemented
   - **Future Enhancement**: Add TOTP-based 2FA for admin accounts

5. **SQLite Limitations**: Not ideal for high-concurrency production use
   - **Recommendation**: Migrate to PostgreSQL for production

## Security Contact

If you discover a security vulnerability, please report it to the system administrator immediately.

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/latest/faq/security.html)

---

**Last Updated**: 2026-01-26
**Version**: 1.0
