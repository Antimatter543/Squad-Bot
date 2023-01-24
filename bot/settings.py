admin_roles = ["Admin"]
elevated_roles = ["UQ Hub Representatives"]
elevated_roles.extend(admin_roles)


def add_admin_role(role: str) -> None:
    """
    Add's the specied role to the list of admin roles

    :param role: the role to add as an admin
    """
    if role not in admin_roles:
        admin_roles.append(role)


def add_elevated_role(role: str) -> None:
    """
    Add's the specied role to the list of elevated roles.

    :param role: the role to add as an admin
    """
    if role not in elevated_roles:
        admin_roles.append(role)
