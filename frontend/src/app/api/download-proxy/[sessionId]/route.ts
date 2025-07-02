import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const { sessionId } = params;
    const { searchParams } = new URL(request.url);
    const filename = searchParams.get('filename');
    
    // Validate session ID format
    if (!sessionId || !/^[a-zA-Z0-9_-]+$/.test(sessionId)) {
      return NextResponse.json(
        { error: 'Invalid session ID format' },
        { status: 400 }
      );
    }

    // Get backend URL
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    // Construct backend download URL
    let downloadUrl = `${backendUrl}/api/download-report/${sessionId}`;
    if (filename) {
      downloadUrl += `?filename=${encodeURIComponent(filename)}`;
    }

    console.log(`[download-proxy] Fetching from backend: ${downloadUrl}`);

    // Fetch file from backend
    const response = await fetch(downloadUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      },
    });

    if (!response.ok) {
      console.error(`[download-proxy] Backend error: ${response.status} ${response.statusText}`);
      
      // Try to get error details
      let errorMessage = 'Download failed';
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.error || errorMessage;
      } catch {
        errorMessage = `Backend error: ${response.status} ${response.statusText}`;
      }

      return NextResponse.json(
        { error: errorMessage },
        { status: response.status }
      );
    }

    // Get the file content
    const fileBuffer = await response.arrayBuffer();
    
    if (!fileBuffer || fileBuffer.byteLength === 0) {
      return NextResponse.json(
        { error: 'Empty file received from backend' },
        { status: 500 }
      );
    }

    // Get filename from Content-Disposition header or use provided filename
    let responseFilename = filename || 'extracted_data.xlsx';
    const contentDisposition = response.headers.get('content-disposition');
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        responseFilename = filenameMatch[1].replace(/['"]/g, '');
      }
    }

    console.log(`[download-proxy] Successfully proxied file: ${responseFilename} (${fileBuffer.byteLength} bytes)`);

    // Return the file with proper headers
    return new NextResponse(fileBuffer, {
      status: 200,
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': `attachment; filename="${responseFilename}"`,
        'Content-Length': fileBuffer.byteLength.toString(),
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      },
    });

  } catch (error) {
    console.error('[download-proxy] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error during download' },
      { status: 500 }
    );
  }
}