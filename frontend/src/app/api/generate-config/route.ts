import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { requirements, sampleDocuments, apiKey } = body;

    // Validate required fields
    if (!requirements) {
      return NextResponse.json(
        { success: false, error: 'Requirements are required for config generation' },
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
    
    console.log(`Generating config via Agno backend at: ${backendUrl}`);
    
    try {
      // Call PromptEngineerWorkflow endpoint
      const response = await fetch(`${backendUrl}/api/generate-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          requirements: requirements,
          sample_documents: sampleDocuments || null
        }),
        signal: req.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Config generation error:', errorText);
        return NextResponse.json(
          { success: false, error: 'Configuration generation failed' },
          { status: response.status }
        );
      }

      const config = await response.json();
      
      return NextResponse.json({
        success: true,
        config: config,
        message: 'Extraction configuration generated successfully'
      });
      
    } catch (fetchError) {
      console.error('Backend connection error:', fetchError);
      return NextResponse.json(
        { success: false, error: 'Failed to connect to configuration service' },
        { status: 500 }
      );
    }

  } catch (error) {
    console.error('Config generation API error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'IntelliExtract Configuration Generator',
    usage: 'POST with { requirements, sampleDocuments?, apiKey? }',
    backend: process.env.AGNO_BACKEND_URL || 'http://localhost:8000'
  });
}