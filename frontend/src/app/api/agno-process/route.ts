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
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    console.log(`Connecting to Agno backend at: ${backendUrl}`);
    
    try {
      // Call the backend agno-process endpoint with JSON data
      const response = await fetch(`${backendUrl}/api/agno-process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          extractedData,
          fileName,
          model,
          llmProvider,
          apiKey: finalApiKey,
          temperature
        }),
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

      // Handle JSON response from backend
      const result = await response.json();
      
      // If backend returned a relative download URL, make it absolute
      if (result.download_url && !result.download_url.startsWith('http')) {
        result.download_url = `${backendUrl}${result.download_url}`;
      }
      
      return NextResponse.json(result);
      
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