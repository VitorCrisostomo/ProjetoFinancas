def is_valid_email(email):
    if not email:
        return False

    if email.count('@') != 1:
        return False
    
    local, domain = email.split("@")

    if not local or  not domain:
        return False

    if '.' not in domain:
        return False

    if local.startswith('.') or domain.startswith('.'):
        return False

    if local.endswith('.') or domain.endswith('.'):
        return False

    if '..' in email:
        return False

    return True
