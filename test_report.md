# Test Execution Report

## Summary

- Total tests: 3
- Passed: 0
- Failed: 3
- Skipped: 0

## Failed Tests Analysis

### test_calculate_geometry_json_via_api_success

**Error Details**:
```
mock_env_vars = None
mock_response = <MagicMock spec='Response' id='2611070396752'>
mock_download_response = <MagicMock spec='Response' id='2611068275728'>
tmp_path = WindowsPath('C:/Users/ciunt/AppData/Local/Temp/pytest-of-ciunt/pytest-1/test_calculate_geometry_json_v0')

    def test_calculate_geometry_json_via_api_success(
        mock_env_vars,
        mock_response,
        mock_download_response,
        tmp_path
    ):
        """Test the successful workflow of converting IFC to JSON geometry."""
        # Setup test files
        ifc_path = tmp_path / "test.ifc"
        output_dir = tmp_path / "output"
        ifc_path.write_text("dummy IFC content")
    
        # Mock the API calls
        with patch('requests.post', return_value=mock_response) as mock_post, \
             patch('requests.get', return_value=mock_download_response) as mock_get:
    
            # Run the function
>           result_path = calculate_geometry_json_via_api(
                ifc_path=str(ifc_path),
                output_dir=str(output_dir)
            )

tests\test_geometry.py:63: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src\qto_buccaneer\geometry.py:60: in calculate_geometry_json_via_api
    _validate_api_key()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

api_key = None

    def _validate_api_key(api_key: Optional[str] = None) -> str:
        """Validate that an API key is available."""
        key = api_key or API_KEY_SECRET
        if not key:
>           raise ValueError(
                "IFC_TO_JSON_API_KEY environment variable not set. "
                "Please set it in your .env file or environment variables. "
                "Contact simon.dilhas@abstract.build to obtain a key."
            )
E           ValueError: IFC_TO_JSON_API_KEY environment variable not set. Please set it in your .env file or environment variables. Contact simon.dilhas@abstract.build to obtain a key.

src\qto_buccaneer\geometry.py:29: ValueError
```

**Suggested Fix**: Update the MetadataFilter implementation to correctly handle these cases.

### test_calculate_geometry_json_via_api_failure

**Error Details**:
```
mock_env_vars = None
tmp_path = WindowsPath('C:/Users/ciunt/AppData/Local/Temp/pytest-of-ciunt/pytest-1/test_calculate_geometry_json_v1')
caplog = <_pytest.logging.LogCaptureFixture object at 0x0000025FDCABAA50>

    def test_calculate_geometry_json_via_api_failure(
        mock_env_vars,
        tmp_path,
        caplog
    ):
        """Test error handling when API request fails."""
        # Setup test files
        ifc_path = tmp_path / "test.ifc"
        output_dir = tmp_path / "output"
        ifc_path.write_text("dummy IFC content")
    
        # Mock a failed API response
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
    
        # Set up logging capture
        caplog.set_level(logging.ERROR)
    
        with patch('requests.post', return_value=mock_response) as mock_post:
            # Run the function
>           result_path = calculate_geometry_json_via_api(
                ifc_path=str(ifc_path),
                output_dir=str(output_dir)
            )

tests\test_geometry.py:109: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src\qto_buccaneer\geometry.py:60: in calculate_geometry_json_via_api
    _validate_api_key()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

api_key = None

    def _validate_api_key(api_key: Optional[str] = None) -> str:
        """Validate that an API key is available."""
        key = api_key or API_KEY_SECRET
        if not key:
>           raise ValueError(
                "IFC_TO_JSON_API_KEY environment variable not set. "
                "Please set it in your .env file or environment variables. "
                "Contact simon.dilhas@abstract.build to obtain a key."
            )
E           ValueError: IFC_TO_JSON_API_KEY environment variable not set. Please set it in your .env file or environment variables. Contact simon.dilhas@abstract.build to obtain a key.

src\qto_buccaneer\geometry.py:29: ValueError
```

**Suggested Fix**: Update the MetadataFilter implementation to correctly handle these cases.

### test_calculate_geometry_json_via_api_download_failure

**Error Details**:
```
mock_env_vars = None
mock_response = <MagicMock spec='Response' id='2611102510608'>
tmp_path = WindowsPath('C:/Users/ciunt/AppData/Local/Temp/pytest-of-ciunt/pytest-1/test_calculate_geometry_json_v2')
caplog = <_pytest.logging.LogCaptureFixture object at 0x0000025FF1D3AD50>

    def test_calculate_geometry_json_via_api_download_failure(
        mock_env_vars,
        mock_response,
        tmp_path,
        caplog
    ):
        """Test error handling when file download fails."""
        # Setup test files
        ifc_path = tmp_path / "test.ifc"
        output_dir = tmp_path / "output"
        ifc_path.write_text("dummy IFC content")
    
        # Mock a failed download response
        mock_download_response = MagicMock(spec=requests.Response)
        mock_download_response.status_code = 404
    
        # Set up logging capture
        caplog.set_level(logging.ERROR)
    
        with patch('requests.post', return_value=mock_response) as mock_post, \
             patch('requests.get', return_value=mock_download_response) as mock_get:
    
            # Run the function
>           result_path = calculate_geometry_json_via_api(
                ifc_path=str(ifc_path),
                output_dir=str(output_dir)
            )

tests\test_geometry.py:154: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src\qto_buccaneer\geometry.py:60: in calculate_geometry_json_via_api
    _validate_api_key()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

api_key = None

    def _validate_api_key(api_key: Optional[str] = None) -> str:
        """Validate that an API key is available."""
        key = api_key or API_KEY_SECRET
        if not key:
>           raise ValueError(
                "IFC_TO_JSON_API_KEY environment variable not set. "
                "Please set it in your .env file or environment variables. "
                "Contact simon.dilhas@abstract.build to obtain a key."
            )
E           ValueError: IFC_TO_JSON_API_KEY environment variable not set. Please set it in your .env file or environment variables. Contact simon.dilhas@abstract.build to obtain a key.

src\qto_buccaneer\geometry.py:29: ValueError
```

**Suggested Fix**: Update the MetadataFilter implementation to correctly handle these cases.
