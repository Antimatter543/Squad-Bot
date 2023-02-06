import pathlib

BASE_DIR = pathlib.Path(__file__).parent

admin_roles = ["Admin"]
elevated_roles = ["UQ Hub Representatives"]


class Settings:
    def __init__(self, bot):
        self.bot = bot

    async def load_settings(self):
        global admin_roles, elevated_roles
        query = (
            "CREATE TABLE IF NOT EXISTS dc_settings (\n"
            "id serial PRIMARY KEY,\n"
            "name VARCHAR(40) NOT NULL,\n"
            "type VARCHAR(40) NOT NULL\n"
            ");"
        )
        async with self.bot.db.acquire() as connection:
            await connection.execute(query)

            query = "SELECT * FROM dc_settings"
            settings = await connection.fetch(query)
            for setting in settings:
                match setting["type"]:
                    case "admin":
                        admin_roles.append(setting["name"])
                    case "elevated":
                        elevated_roles.append(setting["name"])
                    case _:
                        raise NotImplementedError("This role has not been implemented")

    async def add_admin_role(self, role: str) -> None:
        """
        Add's the specied role to the list of admin roles

        :param role: the role to add as an admin
        """
        global admin_roles
        if role not in admin_roles:
            admin_roles.append(role)
            async with self.bot.db.acquire() as connection:
                await connection.execute("INSERT INTO dc_settings VALUES($1,$2)", role, "admin")

    async def remove_admin_role(self, role: str) -> None:
        """
        Removes's the specied role from the list of admin roles

        :param role: the role to remove as an admin
        """
        global admin_roles
        if role in admin_roles:
            admin_roles.remove(role)
            async with self.bot.db.acquire() as connection:
                query = "DELETE FROM dc_settings WHERE name = $1 AND type = $2;"
                await connection.execute(query, role, "admin")

    async def add_elevated_role(self, role: str) -> None:
        """
        Add's the specied role to the list of elevated roles.

        :param role: the role to add as an admin
        """
        global elevated_roles
        if role not in elevated_roles:
            elevated_roles.append(role)
            async with self.bot.db.acquire() as connection:
                await connection.execute("INSERT INTO dc_settings VALUES($1,$2)", role, "elevated")

    async def remove_elevated_role(self, role: str) -> None:
        """
        Removes's the specied role from the list of elevated roles

        :param role: the role to remove as an elevated
        """
        global elevated_roles
        if role in elevated_roles:
            elevated_roles.remove(role)
            async with self.bot.db.acquire() as connection:
                query = "DELETE FROM dc_settings WHERE name = $1 AND type = $2;"
                await connection.execute(query, role, "elevated")
