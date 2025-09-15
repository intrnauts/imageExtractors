"""
Example: Using Image Extractor in a web application (Flask/FastAPI)
"""
from flask import Flask, request, jsonify
import asyncio
import sys
import os

# Add the parent directory to sys.path to import the client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import ImageExtractorClient

app = Flask(__name__)

# Initialize the client
extractor_client = ImageExtractorClient(base_url="http://localhost:8000")

@app.route('/extract-images', methods=['POST'])
def extract_images_endpoint():
    """
    Web endpoint to extract images

    POST /extract-images
    {
        "url": "https://flickr.com/photos/user/123456",
        "size_filter": "Large"  // optional
    }
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400

        url = data['url']
        size_filter = data.get('size_filter')

        # Extract images using async client
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                extractor_client.extract_images(url)
            )

            # Filter by size if requested
            if size_filter:
                filtered_images = [
                    img for img in result['images']
                    if size_filter in img.get('size_label', '')
                ]
                if filtered_images:
                    result['images'] = filtered_images

            return jsonify({
                "success": True,
                "data": result
            })

        finally:
            loop.close()

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/download-image', methods=['POST'])
def download_image_endpoint():
    """
    Download the largest image and return metadata

    POST /download-image
    {
        "url": "https://flickr.com/photos/user/123456",
        "save_path": "/tmp/downloads/"  // optional
    }
    """
    import httpx
    import os

    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400

        url = data['url']
        save_path = data.get('save_path', '/tmp/')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Extract images
            result = loop.run_until_complete(
                extractor_client.extract_images(url)
            )

            if not result['images']:
                return jsonify({"error": "No images found"}), 404

            # Find largest image
            largest = max(result['images'],
                         key=lambda x: x['width'] * x['height'])

            # Download the image
            async def download():
                async with httpx.AsyncClient() as client:
                    response = await client.get(largest['url'])
                    return response.content

            image_data = loop.run_until_complete(download())

            # Save file
            filename = f"image_{largest['width']}x{largest['height']}.jpg"
            filepath = os.path.join(save_path, filename)

            os.makedirs(save_path, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(image_data)

            return jsonify({
                "success": True,
                "filepath": filepath,
                "image_info": largest,
                "metadata": result.get('metadata', {})
            })

        finally:
            loop.close()

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/platforms', methods=['GET'])
def get_platforms():
    """Get supported platforms"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            platforms = loop.run_until_complete(
                extractor_client.get_supported_platforms()
            )
            return jsonify({
                "success": True,
                "platforms": platforms
            })
        finally:
            loop.close()

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print("Starting web app integration example...")
    print("Endpoints:")
    print("  POST /extract-images - Extract images from URL")
    print("  POST /download-image - Download largest image")
    print("  GET /platforms - Get supported platforms")

    app.run(debug=True, port=5000)