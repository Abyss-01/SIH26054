"""Public error explanations; never expose provider payloads or credentials."""


def describe_gemini_error(error: Exception) -> dict:
    """Classify SDK/API failures into fixed, credential-free messages.

    HTTP meanings follow https://ai.google.dev/gemini-api/docs/troubleshooting.
    Provider messages are used only for classification, never displayed/stored.
    """
    code = getattr(error, "code", None)
    if not isinstance(code, int) or isinstance(code, bool) or not 100 <= code <= 599:
        code = None
    hint = str(getattr(error, "message", "") or error).lower()
    classes = {cls.__name__ for cls in type(error).__mro__}
    if "api key" in hint and "leaked" in hint:
        title, action = "API key blocked", "Google reports this key as exposed. Create a replacement key in Google AI Studio, save it here, and test again."
    elif code == 401 or (code == 400 and any(word in hint for word in ("api key not valid", "api_key_invalid", "api key expired", "api_key_expired"))):
        title, action = "API key rejected", "Check or replace the key in Google AI Studio, then save the new key here."
    elif code == 403:
        title, action = "Access denied", "Check the key’s API restrictions and whether its Google Cloud project can access the Gemini API."
    elif code == 429:
        title, action = "Quota or rate limit reached", "Check this project’s Gemini API usage and quota in Google AI Studio. Wait for a rate limit to reset; retrying cannot fix a zero or exhausted daily quota."
    elif code == 404:
        title, action = "Model or endpoint unavailable", "Use Load available models in AI configuration, choose a text model, select Use selected model, then test again."
    elif code in (408, 504) or any("Timeout" in name for name in classes):
        title, action = "Request timed out", "The request did not finish within its timeout. Check connectivity and retry once."
    elif code is not None and code >= 500:
        title, action = "Google service error", "Google could not complete the request. Check the Gemini API service status and try again later."
    elif "certificate" in hint or "SSLError" in classes:
        title, action = "TLS certificate error", "Python could not verify the connection certificate. Check the system certificate store and any HTTPS proxy configuration."
    elif classes & {"ConnectionError", "ConnectError", "NetworkError", "ProxyError", "gaierror"}:
        title, action = "Network connection failed", "The app could not reach Google. Check internet access, DNS, firewall, and proxy settings on the computer running Streamlit."
    elif code == 400:
        title, action = "Request rejected", "Google rejected this request. Check the project’s API setup, region availability, and selected model."
    elif isinstance(error, ValueError) and "provider returned no text" in hint:
        title, action = "Empty model response", "Google returned no usable text, so a successful generation could not be confirmed. Retry the test."
    else:
        title, action = "Client request failed", "The SDK could not complete the request. Check the installed google-genai dependencies and restart Streamlit."
    return {"http_code": code, "title": title, "action": action}


def error_heading(details: dict) -> str:
    code = details.get("http_code")
    return f"HTTP {code} · {details['title']}" if code else details["title"]
