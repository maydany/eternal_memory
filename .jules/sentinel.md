# Sentinel's Journal

## 2024-05-22 - .env Injection via API Key
**Vulnerability:** The `set_api_key` endpoint allowed unvalidated user input to be written directly to the `.env` file, allowing injection of arbitrary environment variables via newline characters.
**Learning:** Even "internal" or "local" configuration files need protection against injection if they are written based on user input. Naive string concatenation for file formats (like `.env`) is dangerous.
**Prevention:** Validate all inputs that are written to files. For `.env` files, ensure values don't contain newlines, or use a proper parser/serializer library that handles escaping.
