import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    // Parse multipart form data
    const formData = await req.formData();
    const files = formData.getAll('files') as File[];
    const extractionRequest = formData.get('request') as string;
    const apiKey = formData.get('apiKey') as string;

    // Validate required fields
    if (!files || files.length === 0) {
      return NextResponse.json(
        { success: false, error: 'At least one file is required' },
        { status: 400 }
      );
    }

    if (!extractionRequest) {
      return NextResponse.json(
        { success: false, error: 'Extraction request is required' },
        { status: 400 }
      );
    }
    
    // Use API key from request or environment
    const finalApiKey = apiKey || process.env.GOOGLE_API_KEY;
    
    if (!finalApiKey) {
      return NextResponse.json(
        { success: false, error: 'API key is required. Please set your Google API key.' },
        { status: 400 }
      );
    }

    // Connect to Agno backend
    const backendUrl = process.env.AGNO_BACKEND_URL || 'http://localhost:8000';
    
    console.log(`Processing ${files.length} files via Agno backend at: ${backendUrl}`);
    
    try {
      // Create form data for backend
      const backendFormData = new FormData();
      
      // Add files
      for (const file of files) {
        backendFormData.append('files', file);
      }
      
      // Add extraction request as JSON string
      backendFormData.append('request', JSON.stringify({
        request: extractionRequest,
        session_id: undefined // Let backend generate session ID
      }));

      // Call Agno backend streaming endpoint
      const response = await fetch(`${backendUrl}/api/extract-data`, {
        method: 'POST',
        body: backendFormData,
        signal: req.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('File processing error:', errorText);
        return NextResponse.json(
          { success: false, error: 'File processing failed' },
          { status: response.status }
        );
      }

      // Handle streaming response
      if (response.headers.get('content-type')?.includes('text/event-stream')) {
        // Stream the response back to the frontend
        const stream = new ReadableStream({
          start(controller) {
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            function pump(): Promise<void> {
              return reader!.read().then(({ done, value }) => {
                if (done) {
                  controller.close();
                  return;
                }

                // Forward the chunk to the frontend
                const chunk = decoder.decode(value);
                controller.enqueue(new TextEncoder().encode(chunk));
                return pump();
              });
            }

            return pump();
          }
        });

        return new Response(stream, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
          },
        });
      } else {
        // Handle non-streaming response
        const result = await response.json();
        return NextResponse.json(result);
      }
      
    } catch (fetchError) {
      console.error('Backend connection error:', fetchError);
      return NextResponse.json(
        { success: false, error: 'Failed to connect to processing service' },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('Upload API error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'IntelliExtract File Upload & Processing',
    usage: 'POST with multipart/form-data: files, request, apiKey?',
    backend: process.env.AGNO_BACKEND_URL || 'http://localhost:8000'
  });
}