import pyodbc
from core.logger import log_message 
import json

with open(r'config.json', 'r') as f:
    config = json.load(f)

server = config['server']
database = config['database']
driver = config['driver']    

def get_connection():
    """Create a connection to the SQL Server database."""
    try:
        connection_string = f"""
            DRIVER={driver};
            SERVER={server};
            DATABASE={database};
            Trusted_Connection=yes;
            """
        connection = pyodbc.connect(connection_string)
        return connection
    except Exception as e:
        log_message(f"ERROR: Failed to connect to the database {e}", 1)
        raise e
    
def get_create_table_query():
    """
    Returns the SQL query to create the required tables in the database."""
    # create tables 
    # 1. product(id PRIMARY_KEY, asin UNIQUE, title, description, occasion, product_dimensions, )
    # 2. images(image_id, product_id, image_link)
    # 3. product_details(id, product_id {dynamic-columns})

    create_tables_query = """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'products')
            BEGIN
                CREATE TABLE products (
                    product_id INT IDENTITY(1,1) PRIMARY KEY,
                    asin VARCHAR(10) UNIQUE NOT NULL,
                    title VARCHAR(255),
                    description TEXT
                );
            END;

            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'images')
            BEGIN
                CREATE TABLE images (
                    image_id INT PRIMARY KEY IDENTITY(1,1),
                    product_id INT,
                    image_link TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                );
            END;
            
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'product_details')
            BEGIN
                CREATE TABLE product_details (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    product_id INT,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                );
            END;
            
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'product_overview')
            BEGIN
                CREATE TABLE product_overview (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    product_id INT,
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                );
            END;
            
        """
    return create_tables_query

def check_if_product_already_exists(asin_list):
    """ Check if the products already exist in the database.

    Args:
        asin_list (list): List of ASINs to check

    Returns:
        new_product_list (list): List of ASINs that do not exist in the database
    """
    conn = None
    new_product_list = []
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        table_check_query = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?;"
        
        cursor.execute(table_check_query, ('products',))
        table_exists = cursor.fetchone()[0] > 0

        if table_exists:
            for asin in asin_list:
                cursor.execute("SELECT COUNT(*) FROM products WHERE asin = ?", asin)
                exists = cursor.fetchone()[0]

                if not exists:
                    new_product_list.append(asin)
    except Exception as e:
        log_message(f"ERROR: Failed to check if products already exist: {e}", 1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return new_product_list

def create_tables():
    """ Create the required tables in the database.

    Raises:
        db_error: An error occurred while creating the tables
        e: An unexpected error occurred
    """
    conn = None
    try:
        conn = get_connection()  
        create_tables_query = get_create_table_query()  

        with conn.cursor() as cursor:
            cursor.execute(create_tables_query)
            # log_message("EXEC: Tables created successfully", 0)
            conn.commit()  
    except Exception as e:
        log_message(f"ERROR: Failed to create tables: {e}", 1)
    finally:
        if conn:
            conn.close()
            
def update_product(product, conn, cursor, product_id):
    """ Update existing product in the database."""
    
    update_products_query = """
        UPDATE products
        SET title = ?, description = ?, occasion = ?, product_dimensions = ?
        WHERE asin = ?;
    """
    update_images_query = """
        UPDATE images 
        SET image_link = ?
        WHERE product_id = ?;
    """
    update_details_query = f"""
        UPDATE product_details
        SET ? = ?
        WHERE product_id = ?;"""
    asin = product.get('ASIN')
    title = product.get('title')
    description = product.get('description')
    occasion = product['table_info'].get('Occasion')
    product_dimensions = product['table_info'].get('Product Dimensions')
    image_links = product.get('image_links')
    table_info = product.get('table_info')
    
    cursor.execute(update_products_query, (title, description, occasion, product_dimensions, asin))
    log_message(f"EXEC: Updated product with ASIN {asin}", 0)
    
    for link in image_links:
        cursor.execute(update_images_query, (link, product_id))
        
    

def insert_data(product_list):
    """ Insert the scraped product data into the database."""

    insert_products = """
        INSERT INTO products (asin, title, description)
        VALUES (?, ?, ?);
        SELECT SCOPE_IDENTITY();  -- Retrieve the ID of the newly inserted product
    """
    
    check_asin_exists = "SELECT product_id FROM products WHERE asin = ?;"
    
    conn = None
    try:
        conn = get_connection() 
        cursor = conn.cursor()  
        
        for product in product_list:
            asin = product.get('ASIN')
            title = product.get('title')
            description = product.get('description')
            # occasion = product['table_info'].get('Occasion')
            # product_dimensions = product['table_info'].get('Product Dimensions')
            image_links = product.get('image_links')
            # table_info = product.get('table_info')
            description_table = product.get('description_table')
            overview_table = product.get('overview_table')
            
            if asin and title:
                try:
                    cursor.execute(check_asin_exists, (asin,))
                    # p_id = cursor.fetchone()[0]
                    p_id = cursor.fetchone()
                    if p_id:
                        log_message(f"INFO: ASIN {asin} already exists in the database. Skipping insertion.", 0)
                        # update_product(product, conn, cursor, p_id)
                        continue

                    cursor.execute(insert_products, (asin, title, description))
                    
                    cursor.execute("SELECT product_id FROM products WHERE asin = ?", asin)
                    product_id_row = cursor.fetchone()

                    if product_id_row:
                        product_id = product_id_row[0]
                        
                        for image_link in image_links:
                            cursor.execute(
                                "INSERT INTO images (product_id, image_link) VALUES (?, ?);",
                                (product_id, image_link)
                            )
                        insert_dynamic_data(product_id, description_table,'product_details', conn, cursor)
                        
                        insert_dynamic_data(product_id, overview_table,'product_overview', conn, cursor)
                        
                        log_message(f"EXEC: Inserted {len(image_links)} images for product with ASIN {asin}", 0)
                except Exception as e:
                    log_message(f"ERROR: Failed to insert ASIN {asin}: {e}", 1)
                    conn.rollback()
                    raise e
            else:
                log_message(f"ERROR: Missing required fields for ASIN {asin}. Skipping insertion.", 1)
        conn.commit()

    except pyodbc.Error as db_error:
        log_message(f"ERROR: Database error occurred: {db_error}", 1)
        conn.rollback()
    except Exception as e:
        log_message(f"ERROR: Failed to insert products: {e}", 1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
def insert_dynamic_data(product_id, table_info, table_name, conn, cursor):
    """ Insert the dynamic product details into the database."""
    cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}';")
    existing_columns = [row[0] for row in cursor.fetchall()]

    try:
        for key in table_info.keys():
            if key not in existing_columns:
                alter_table_query = f"ALTER TABLE {table_name} ADD [{key}] NVARCHAR(MAX);"
                cursor.execute(alter_table_query)
                log_message(f"EXEC: Added missing column '{key}' to '{table_name}' table.", 0)
        
        column_names = ', '.join([f"[{key}]" for key in table_info.keys()])
        placeholders = ', '.join(['?'] * len(table_info))
        values = list(table_info.values())
        
        insert_query = f"""
            INSERT INTO {table_name} (product_id, {column_names})
            VALUES (?, {placeholders});
        """
        cursor.execute(insert_query, (product_id, *values))
        log_message(f"EXEC: Inserted data into '{table_name}' for product_id {product_id}.", 0)
        
        conn.commit()
    except pyodbc.Error as db_error:
        log_message(f"ERROR: Database error occurred: {db_error}", 1)
        conn.rollback()
        raise db_error
    except Exception as e:
        log_message(f"ERROR: Failed to insert data: {e}", 1)
        conn.rollback()
        raise e

def store_data(product_list):
    create_tables()
    insert_data(product_list)

# def insert_images(product_asin, image_links, cursor):
#     try:
#         cursor.execute("SELECT id FROM products WHERE asin = ?", product_asin)
#         product_id_row = cursor.fetchone()
#         if product_id_row:
#             product_id = product_id_row[0]  # Extract the product ID
#             if not image_links:
#                 log_message(f"INFO: No images to insert for ASIN {product_asin}.", 0)
#                 return
#             for image_link in image_links:
#                 cursor.execute(
#                     "INSERT INTO images (product_id, image_link) VALUES (?, ?);",
#                     (product_id, image_link)
#                 )
#             log_message(f"EXEC: Inserted {len(image_links)} images for product with ASIN {product_asin}", 0)
#             conn.commit()  # Commit after inserting all images
#         else:
#             log_message(f"ERROR: Product with ASIN {product_asin} not found in the database", 1)
#     except pyodbc.Error as db_error:
#         log_message(f"ERROR: Database error occurred: {db_error}", 1)
#         if conn:
#             conn.rollback()  # Rollback if error occurs
#         raise db_error
#     except Exception as e:
#         log_message(f"ERROR: Failed to insert images: {e}", 1)
#         if conn:
#             conn.rollback()
#         raise e
#     # finally:
#     #     if cursor:
#     #         cursor.close()  # Ensure cursor is closed
#     #     if conn:
#     #         conn.close()  # Ensure connection is closed

