import pandas as pd
from pathlib import Path
import sys
from datetime import datetime
import traceback
import json
import requests
import shutil
from dotenv import load_dotenv
import os
import plotly.graph_objects as go


load_dotenv()

API_URL = os.getenv("BUILDING_ENVELOP_CHECK_API_URL")

def _print_with_flush(*args, **kwargs):
    """Print with immediate flush to ensure output is visible"""
    print(*args, **kwargs, flush=True)

def _visualize_geometry(target_file: Path, reference_file: Path, api_url: str = API_URL):
    """Visualize the building geometry and max volume using Plotly"""
    _print_with_flush("\n" + "="*50)
    _print_with_flush("INITIALIZING VISUALIZATION PROCESS...")
    _print_with_flush("="*50 + "\n")
    
    start_time = datetime.now()
    _print_with_flush(f"Starting visualization process at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    _print_with_flush(f"Current working directory: {Path.cwd()}")
    
    _print_with_flush(f"\n📁 Processing files:")
    _print_with_flush(f"   Target file: {target_file}")
    _print_with_flush(f"   Reference file: {reference_file}")
    _print_with_flush(f"   API URL: {api_url}")
    
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    _print_with_flush(f"\n📁 Created/verified output directory: {output_dir}")
    
    # Generate base filename from target file
    base_filename = f"{target_file.stem}_max_check"
    _print_with_flush(f"📝 Generated base filename: {base_filename}")
    
    # Prepare files for upload
    _print_with_flush("\n📤 Preparing files for upload...")
    try:
        files = {
            'target_file': (target_file.name, open(target_file, 'rb'), 'application/octet-stream'),
            'reference_file': (reference_file.name, open(reference_file, 'rb'), 'application/octet-stream')
        }
    except Exception as e:
        _print_with_flush(f"❌ Error opening files: {str(e)}")
        _print_with_flush("Stack trace:")
        _print_with_flush(traceback.format_exc())
        sys.exit(1)
    
    try:
        # Get geometry data from API
        _print_with_flush("\n🌐 Fetching geometry data from API...")
        _print_with_flush(f"   Making POST request to {api_url}/visualize")
        try:
            response = requests.post(f"{api_url}/visualize", files=files)
            _print_with_flush(f"   Response status code: {response.status_code}")
            _print_with_flush(f"   Response headers: {dict(response.headers)}")
            
            if response.status_code == 400:
                _print_with_flush(f"❌ Error: {response.json()['detail']}")
                sys.exit(1)
            elif response.status_code == 500:
                _print_with_flush(f"❌ Server error: {response.json()['detail']}")
                sys.exit(1)
                
            response.raise_for_status()
            data = response.json()
            _print_with_flush("✅ Successfully received data from API")
            _print_with_flush(f"   Received data keys: {list(data.keys())}")
            
        except requests.exceptions.ConnectionError as e:
            _print_with_flush(f"❌ Connection error: Could not connect to {api_url}")
            _print_with_flush(f"   Error details: {str(e)}")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            _print_with_flush(f"❌ Request error: {str(e)}")
            _print_with_flush("Stack trace:")
            _print_with_flush(traceback.format_exc())
            sys.exit(1)
        
        _print_with_flush("\n🎨 Creating 3D visualization...")
        # Create figure
        fig = go.Figure()
        
        # Add max volume
        _print_with_flush("   Adding max volume to visualization...")
        try:
            max_volume = data['max_volume']
            fig.add_trace(go.Mesh3d(
                x=max_volume['x'],
                y=max_volume['y'],
                z=max_volume['z'],
                i=max_volume['i'],
                j=max_volume['j'],
                k=max_volume['k'],
                color='green',
                opacity=0.15,
                name='Max Volume',
                showscale=False,
                hoverinfo='skip',
                flatshading=True,
                lighting=dict(
                    ambient=0.8,
                    diffuse=0.9,
                    fresnel=0.1,
                    roughness=0.1,
                    specular=0.2
                )
            ))
        except KeyError as e:
            _print_with_flush(f"❌ Missing key in max_volume data: {str(e)}")
            _print_with_flush(f"Available keys: {list(data['max_volume'].keys())}")
            sys.exit(1)
        
        # Add building elements
        _print_with_flush(f"   Adding {len(data['building_elements'])} building elements to visualization...")
        for i, element in enumerate(data['building_elements']):
            try:
                fig.add_trace(go.Mesh3d(
                    x=element['x'],
                    y=element['y'],
                    z=element['z'],
                    i=element['i'],
                    j=element['j'],
                    k=element['k'],
                    color='grey',
                    opacity=1.0,
                    name=f'Building Element {i+1}',
                    hoverinfo='skip',
                    lighting=dict(
                        ambient=0.8,
                        diffuse=0.9,
                        fresnel=0.1,
                        roughness=0.1,
                        specular=0.2
                    )
                ))
            except KeyError as e:
                _print_with_flush(f"❌ Missing key in building element {i}: {str(e)}")
                _print_with_flush(f"Available keys: {list(element.keys())}")
                sys.exit(1)
        
        _print_with_flush("   Configuring visualization layout...")
        # Update layout
        fig.update_layout(
            title=f"{target_file.stem} - Max Volume Check",
            scene=dict(
                aspectmode='data',
                xaxis=dict(showgrid=True, showbackground=False, showticklabels=False, title=''),
                yaxis=dict(showgrid=True, showbackground=False, showticklabels=False, title=''),
                zaxis=dict(showgrid=True, showbackground=False, showticklabels=False, title=''),
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
                bgcolor='white'
            ),
            showlegend=True,
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        _print_with_flush("\n💾 Saving output files...")
        try:
            # Save HTML file
            html_output = output_dir / f"{base_filename}.html"
            fig.write_html(html_output)
            _print_with_flush(f"   ✅ HTML visualization saved to: {html_output}")
            
            # Save JSON file
            json_output = output_dir / f"{base_filename}.json"
            with open(json_output, 'w') as f:
                json.dump(fig.to_json(), f)
            _print_with_flush(f"   ✅ Plotly graph JSON saved to: {json_output}")
        except Exception as e:
            _print_with_flush(f"❌ Error saving output files: {str(e)}")
            _print_with_flush("Stack trace:")
            _print_with_flush(traceback.format_exc())
            sys.exit(1)
        
        end_time = datetime.now()
        duration = end_time - start_time
        _print_with_flush("\n" + "="*50)
        _print_with_flush(f"✨ Visualization process completed successfully!")
        _print_with_flush(f"⏱️  Total processing time: {duration.total_seconds():.2f} seconds")
        _print_with_flush("="*50 + "\n")
        
        return html_output, json_output

    except Exception as e:
        _print_with_flush(f"\n❌ Unexpected error: {str(e)}")
        _print_with_flush("Stack trace:")
        _print_with_flush(traceback.format_exc())
        sys.exit(1)
    finally:
        # Close file handles
        for file in files.values():
            file[1].close()


def _validate_api_response(response: requests.Response) -> tuple[bool, str]:
    """Validate the API response and return (is_valid, error_message)"""
    if response.status_code == 400:
        try:
            error_detail = response.json().get('detail', 'Unknown error')
            return False, f"API validation error: {error_detail}"
        except:
            return False, f"API validation error (status {response.status_code})"
    elif response.status_code == 500:
        try:
            error_detail = response.json().get('detail', 'Unknown error')
            return False, f"API server error: {error_detail}"
        except:
            return False, f"API server error (status {response.status_code})"
    elif response.status_code != 200:
        return False, f"Unexpected API response (status {response.status_code})"
    return True, ""

def check_building_inside_envelop(
        target_file: Path, 
        reference_file: Path, 
        output_base_dir: Path, 
        api_url: str = API_URL) -> dict:
    """Process a single IFC file and return its results"""
    try:
        # Create timestamp for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory for this file
        file_output_dir = output_base_dir / "visualizations" / target_file.stem
        file_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate files before processing
        if not target_file.exists():
            return {
                'filename': target_file.name,
                'timestamp': timestamp,
                'html_path': None,
                'json_path': None,
                'status': 'error',
                'error_message': f"Target file not found: {target_file}",
                'volume_check': None
            }
        
        if not reference_file.exists():
            return {
                'filename': target_file.name,
                'timestamp': timestamp,
                'html_path': None,
                'json_path': None,
                'status': 'error',
                'error_message': f"Reference file not found: {reference_file}",
                'volume_check': None
            }
        
        # Check if files are different
        if target_file == reference_file:
            return {
                'filename': target_file.name,
                'timestamp': timestamp,
                'html_path': None,
                'json_path': None,
                'status': 'error',
                'error_message': "Target and reference files are the same",
                'volume_check': None
            }
        
        # First check volume containment
        _print_with_flush("\n📏 Checking volume containment...")
        try:
            with open(target_file, 'rb') as tf, open(reference_file, 'rb') as rf:
                files = {
                    'target_file': (target_file.name, tf, 'application/octet-stream'),
                    'reference_file': (reference_file.name, rf, 'application/octet-stream')
                }
                volume_response = requests.post(f"{api_url}/check-volume", files=files)
                volume_response.raise_for_status()
                volume_check = volume_response.json()
                _print_with_flush(f"   Volume check result: {'✅ Success' if volume_check['success'] else '❌ Failed'}")
                if not volume_check['success']:
                    _print_with_flush(f"   Reason: {volume_check.get('reason', 'Unknown')}")
                    _print_with_flush(f"   Outside elements: {volume_check.get('outside_elements', 0)}")
        except Exception as e:
            _print_with_flush(f"❌ Volume check error: {str(e)}")
            volume_check = None
        
        # Process the file for visualization
        html_path, json_path = _visualize_geometry(
            target_file=target_file,
            reference_file=reference_file,
            api_url=api_url
        )

        building_name = target_file.stem
        building_name = building_name.replace("_abstractBIM", "")
        
        # Move files to the correct output directory
        new_html_path = file_output_dir / f"{target_file.stem}_visualization.html"
        new_json_path = file_output_dir / f"{target_file.stem}_data.json"
        
        shutil.move(html_path, new_html_path)
        shutil.move(json_path, new_json_path)
        
        # Read the JSON data to get volume information
        with open(new_json_path, 'r') as f:
            plotly_data = json.load(f)
        
        # Determine status based on volume check
        status = 'success' if volume_check and volume_check.get('success', False) else 'error'
        error_message = None if status == 'success' else (volume_check.get('reason', 'Unknown error') if volume_check else 'Volume check failed')
        
        # Extract relevant information
        result = {
            'filename': target_file.name,
            'building_name': building_name,
            'timestamp': timestamp,
            'html_path': str(new_html_path),
            'json_path': str(new_json_path),
            'status': status,
            'error_message': error_message,
            'volume_check': volume_check
        }
        
        return result
        
    except requests.exceptions.ConnectionError as e:
        return {
            'filename': target_file.name,
            'building_name': building_name,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'html_path': None,
            'json_path': None,
            'status': 'error',
            'error_message': f"Could not connect to API: {str(e)}",
            'volume_check': None
        }
    except Exception as e:
        return {
            'filename': target_file.name,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'html_path': None,
            'json_path': None,
            'status': 'error',
            'error_message': f"Processing error: {str(e)}",
            'volume_check': None
        }

def _write_results_to_excel(results: list, output_dir: Path, excel_filename: str = "report.xlsx") -> Path:
    """
    Write processing results to an Excel file with formatting.
    
    Args:
        results: List of result dictionaries from check_building_inside_envelop
        output_dir: Directory to save the Excel file
        excel_filename: Name of the Excel file (default: "report.xlsx")
        
    Returns:
        Path: Path to the created Excel file
    """
    _print_with_flush("\n📊 Generating Excel report...")
    df = pd.DataFrame(results)
    df.drop(columns=['json_path', 'volume_check', 'timestamp'], inplace=True)
    excel_path = output_dir / excel_filename
    
    # Create Excel writer with xlsxwriter engine
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Processing Results', index=False)
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Processing Results']
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1
        })
        
        error_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006'
        })
        
        success_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'font_color': '#006100'
        })
        
        link_format = workbook.add_format({
            'color': 'blue',
            'underline': True
        })
        
        # Write the header with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)  # Set column width
        
        # Add conditional formatting for status column
        status_col = df.columns.get_loc('status')
        worksheet.conditional_format(1, status_col, len(df) + 1, status_col, {
            'type': 'cell',
            'criteria': '=',
            'value': '"success"',
            'format': success_format
        })
        worksheet.conditional_format(1, status_col, len(df) + 1, status_col, {
            'type': 'cell',
            'criteria': '=',
            'value': '"error"',
            'format': error_format
        })
        
        # Add hyperlinks to HTML files
        html_col = df.columns.get_loc('html_path')
        for row_num, html_path in enumerate(df['html_path'], start=1):
            if html_path:  # Only add link if path exists
                # Use relative path from Excel file to HTML file
                rel_path = Path(html_path).relative_to(output_dir)
                # Convert to forward slashes and add file:// protocol
                file_url = 'file://' + str(rel_path).replace('\\', '/')
                worksheet.write_url(row_num, html_col, file_url, link_format, 'Open Visualization')
    
    _print_with_flush(f"✅ Excel report saved to: {excel_path}")
    return excel_path

def process_check_building_inside_envelop(ifc_dir: Path, reference_file: Path, output_dir: Path, api_url: str = API_URL):
    """Process all IFC files in the specified directory"""
    start_time = datetime.now()
    results = []
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    vis_output_dir = output_dir / "visualizations"
    vis_output_dir.mkdir(exist_ok=True)
    
    # Get list of IFC files
    ifc_files = list(ifc_dir.glob("*.ifc"))
    if not ifc_files:
        _print_with_flush(f"❌ No IFC files found in {ifc_dir}")
        return
    
    _print_with_flush(f"\n📁 Found {len(ifc_files)} IFC files to process")
    
    for i, ifc_file in enumerate(ifc_files, 1):
        _print_with_flush(f"\n{'='*30}")
        _print_with_flush(f"Processing file {i}/{len(ifc_files)}: {ifc_file.name}")
        _print_with_flush(f"{'='*30}")
        
        result = check_building_inside_envelop(
            target_file=ifc_file,
            reference_file=reference_file,
            output_base_dir=output_dir,
            api_url=api_url
        )
        results.append(result)
        
        if result['status'] == 'success':
            _print_with_flush(f"✅ Successfully processed {ifc_file.name} (building is within max volume)")
        else:
            _print_with_flush(f"❌ Error processing {ifc_file.name}: {result['error_message']}")
    
    # Write results to Excel
    excel_path = _write_results_to_excel(results, output_dir)
    
    # Print summary
    end_time = datetime.now()
    duration = end_time - start_time
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    _print_with_flush("\n" + "="*50)
    _print_with_flush("BATCH PROCESSING COMPLETED")
    _print_with_flush("="*50)
    _print_with_flush(f"Total files processed: {len(results)}")
    _print_with_flush(f"Successful (within max volume): {success_count}")
    _print_with_flush(f"Failed (outside max volume): {error_count}")
    _print_with_flush(f"Total processing time: {duration.total_seconds():.2f} seconds")
    _print_with_flush(f"Visualizations directory: {vis_output_dir}")
    _print_with_flush(f"Excel report: {excel_path}")
    _print_with_flush("="*50 + "\n")

    df = pd.DataFrame(results)
    return df

if __name__ == "__main__":
    # Configuration
    IFC_DIR = Path("ifc_files")
    REFERENCE_FILE = Path("ifc_files/max.ifc")
    OUTPUT_DIR = Path("batch_output")
    
    _print_with_flush("\n🚀 STARTING BATCH PROCESSING SCRIPT...")
    _print_with_flush("="*50)
    _print_with_flush(f"Python version: {sys.version}")
    _print_with_flush(f"Current working directory: {Path.cwd()}")
    
    # Check if directories and files exist
    if not IFC_DIR.exists():
        _print_with_flush(f"❌ IFC directory not found: {IFC_DIR}")
        sys.exit(1)
    if not REFERENCE_FILE.exists():
        _print_with_flush(f"❌ Reference file not found: {REFERENCE_FILE}")
        sys.exit(1)
    
    # Run batch processing
    process_check_building_inside_envelop(
        ifc_dir=IFC_DIR,
        reference_file=REFERENCE_FILE,
        output_dir=OUTPUT_DIR
    ) 