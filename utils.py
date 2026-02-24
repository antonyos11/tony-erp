import json
from functools import wraps
from django.http import QueryDict
from django.views.decorators.csrf import csrf_exempt

def handle_json_request(view_func):
    """
    Middleware/Decorator to handle JSON requests.
    If the content-type is application/json, it parses the body 
    and adds it to request.POST so that forms can handle it transparently.
    """
    @csrf_exempt
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        print(f"DEBUG: Content-Type: {request.content_type}")
        if request.content_type == 'application/json':
            print("DEBUG: processing JSON body")
            try:
                data = json.loads(request.body)
                print(f"DEBUG: JSON body: {data}")
                # Create a mutable QueryDict from the JSON data
                q_data = QueryDict('', mutable=True)
                for key, value in data.items():
                    # Handle boolean values often sent as boolean in JSON but need to be 'on' or 'True' for some Django fields,
                    # or just passed as is. Django forms usually expect string values for checks.
                    if isinstance(value, bool):
                        if value:
                            q_data[key] = 'on'  # Standard HTML checkbox behavior
                            # Also add 'True' just in case, though 'on' is standard for CheckboxInput
                    elif isinstance(value, list) or isinstance(value, dict):
                         # For complex data, we might need more handling, 
                         # but for simple forms, we just pass the value.
                         # This might need adjustment if forms expect multiple values.
                         pass 
                    else:
                        q_data[key] = str(value)
                
                # Retrieve any existing POST data (unlikely for JSON, but safe to check)
                q_data.update(request.POST) 
                
                # Override request.POST
                request.POST = q_data
            except json.JSONDecodeError:
                pass # Fallback to standard handling if JSON is invalid
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view
