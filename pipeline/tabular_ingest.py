import pandas as pd
import sqlparse
import pathlib
import os

def extract_tabular_data(file_path: str) -> list[dict]:
    """
    Extract data from CSV, Excel, or SQL files and return a list of dictionaries
    ready to be converted to LangChain Documents.
    """
    path = pathlib.Path(file_path)
    ext = path.suffix.lower()
    filename = path.name

    if ext == ".csv":
        return _process_pandas(file_path, filename, pd.read_csv(file_path), "CSV")
    elif ext in [".xlsx", ".xls"]:
        # Handle multiple sheets
        xls = pd.ExcelFile(file_path)
        all_chunks = []
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            all_chunks.extend(_process_pandas(file_path, filename, df, sheet_name))
        return all_chunks
    elif ext == ".sql":
        return _process_sql(file_path, filename)
    else:
        raise ValueError(f"Unsupported tabular extension: {ext}")

def _process_pandas(file_path: str, filename: str, df: pd.DataFrame, table_name: str) -> list[dict]:
    chunks = []
    
    # Handle empty dataframe
    if df.empty:
        return chunks

    columns = df.columns.tolist()
    columns_str = ", ".join(str(c) for c in columns)
    
    # Generate schema chunk
    dtypes_str = ", ".join([f"{col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)])
    total_rows = len(df)
    
    # Sample first 3 rows
    sample_rows = []
    for i, row in df.head(3).iterrows():
        row_str = " | ".join(f"{col}={row[col]}" for col in columns)
        sample_rows.append(f"Row {i}: {row_str}")
    sample_text = "\n".join(sample_rows)
    
    schema_text = f"[Schema: {filename}] Columns: {dtypes_str} | Total rows: {total_rows} | Sample: {sample_text}"
    
    chunks.append({
        "text": schema_text,
        "metadata": {
            "source": filename,
            "data_type": "tabular",
            "table_name": table_name,
            "chunk_type": "schema_summary",
            "column_names": columns_str
        }
    })
    
    # Generate row chunks
    for i, row in df.iterrows():
        row_str = " | ".join(f"{col}={row[col]}" for col in columns)
        chunk_text = f"[Table: {filename}] Row {i}: {row_str}"
        
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "source": filename,
                "data_type": "tabular",
                "table_name": table_name,
                "row_index": i,
                "column_names": columns_str
            }
        })
        
    return chunks

def _process_sql(file_path: str, filename: str) -> list[dict]:
    chunks = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
        
    statements = sqlparse.split(sql_content)
    
    # Very basic SQL extraction for CREATE TABLE and INSERT INTO
    # Real SQL parsing is complex, this targets the specific prompt requirements
    create_statements = []
    insert_statements = []
    
    for stmt in statements:
        parsed = sqlparse.parse(stmt)
        if not parsed:
            continue
        statement = parsed[0]
        token_type = statement.get_type()
        if token_type == 'CREATE':
            create_statements.append(stmt.strip())
        elif token_type == 'INSERT':
            insert_statements.append(stmt.strip())
            
    # Schema chunk
    schema_text = f"[Schema: {filename}] CREATE Statements:\n" + "\n".join(create_statements)
    
    chunks.append({
        "text": schema_text,
        "metadata": {
            "source": filename,
            "data_type": "tabular",
            "table_name": "SQL_DUMP",
            "chunk_type": "schema_summary",
            "column_names": "N/A"
        }
    })
    
    # Data chunks (each INSERT is treated as a chunk)
    for i, insert_stmt in enumerate(insert_statements):
        chunk_text = f"[Table: {filename}] INSERT Statement {i}: {insert_stmt}"
        
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "source": filename,
                "data_type": "tabular",
                "table_name": "SQL_DUMP",
                "row_index": i,
                "column_names": "N/A"
            }
        })
        
    return chunks
