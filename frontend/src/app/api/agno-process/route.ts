import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { extractedData, fileName, llmProvider, model, apiKey, temperature } = body;

    // Validate required fields
    if (!extractedData || !fileName || !model) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields: extractedData, fileName, or model' },
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
    
    console.log(`Connecting to Agno backend at: ${backendUrl}`);
    
    try {
      // Create form data for file upload to match backend expectations
      const formData = new FormData();
      
      // Create a blob from the extracted data to simulate file upload
      const dataBlob = new Blob([JSON.stringify(extractedData, null, 2)], { 
        type: 'application/json' 
      });
      formData.append('files', dataBlob, fileName.replace(/\.[^/.]+$/, '.json'));
      
      // Add extraction request
      formData.append('request', JSON.stringify({
        request: `Process this document data: ${JSON.stringify(extractedData).substring(0, 500)}...`,
        session_id: undefined // Let backend generate session ID
      }));

      // Call Agno backend streaming endpoint
      const response = await fetch(`${backendUrl}/api/extract-data`, {
        method: 'POST',
        headers: {
          // Don't set Content-Type - let browser set it for FormData
        },
        body: formData,
        signal: req.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Agno backend error:', errorText);
        return NextResponse.json(
          { success: false, error: 'Data processing failed' },
          { status: response.status }
        );
      }

      // Handle streaming response
      if (response.headers.get('content-type')?.includes('text/event-stream')) {
        // For streaming responses, we'll collect all events and return final result
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let result = '';
        let sessionId = '';

        if (reader) {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              
              const chunk = decoder.decode(value);
              const lines = chunk.split('\n');
              
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6);
                  try {
                    const parsed = JSON.parse(data);
                    if (parsed.status === 'completed' && parsed.session_id) {
                      sessionId = parsed.session_id;
                    }
                  } catch {
                    // Append text data
                    result += data + '\n';
                  }
                }
              }
            }
          } finally {
            reader.releaseLock();
          }
        }

        return NextResponse.json({
          success: true,
          message: 'Data processed successfully',
          result: result.trim(),
          session_id: sessionId,
          download_url: sessionId ? `${backendUrl}/api/download-report/${sessionId}` : null,
          token_usage: {
            input_tokens: 0,
            output_tokens: 0, 
            total_tokens: 0
          },
          processingCost: 0
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
    console.error('API route error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}