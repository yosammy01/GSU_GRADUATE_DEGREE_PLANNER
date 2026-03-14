# Use the official MySQL 8.0 image as the foundation
FROM mysql:8.0

# Set environment variables for the initial database setup.
# These match the credentials used in your Flask app connection strings.
ENV MYSQL_ROOT_PASSWORD=super_secret_root_password
ENV MYSQL_DATABASE=gsu_catalog
ENV MYSQL_USER=flask_user
ENV MYSQL_PASSWORD=your_secure_password

# Expose the standard MySQL port for internal container networking
EXPOSE 3306

# AUTOMATION STEP:
# This copies your prenumbered SQL scripts (01_schema, 02_catalog, etc.)
# into the initialization directory. MySQL executes these in alphabetical 
# order on the very first startup to build your entire database automatically.
# This assumes the "DB_Scripts" folder is inside your "DB_Server" directory.
COPY ./DB_Scripts/ /docker-entrypoint-initdb.d/