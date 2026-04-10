# Use the official MySQL 8.0 image as the foundation
FROM mysql:8.0

# Expose the standard MySQL port for internal container networking
EXPOSE 3306

# AUTOMATION STEP:
# This copies prenumbered SQL scripts (01_schema, 02_catalog, etc.)
# into the initialization directory. MySQL executes these in alphabetical 
# order on the very first startup to build entire database automatically.
# This assumes the "DB_Scripts" folder is inside "DB_Server" directory.
COPY ./DB_Scripts/ /docker-entrypoint-initdb.d/