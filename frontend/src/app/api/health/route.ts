import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  try {
    const backendUrl = process.env.AGNO_BACKEND_URL || 'http://localhost:8000';
    
    console.log(`Checking health of Agno backend at: ${backendUrl}`);
    
    try {
      // Check backend health
      const response = await fetch(`${backendUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      if (!response.ok) {
        return NextResponse.json({
          success: false,
          frontend: 'healthy',
          backend: 'unhealthy',
          backend_url: backendUrl,
          backend_status: response.status,
          error: 'Backend health check failed'
        }, { status: 502 });
      }

      const backendHealth = await response.json();
      
      return NextResponse.json({
        success: true,
        frontend: 'healthy',
        backend: 'healthy',
        backend_url: backendUrl,
        backend_info: backendHealth,
        api_key_configured: !!process.env.GOOGLE_API_KEY,
        timestamp: new Date().toISOString()
      });
      
    } catch (fetchError) {
      console.error('Backend health check failed:', fetchError);
      return NextResponse.json({
        success: false,
        frontend: 'healthy',
        backend: 'unreachable',
        backend_url: backendUrl,
        error: 'Cannot connect to backend service',
        details: fetchError instanceof Error ? fetchError.message : 'Unknown error'
      }, { status: 502 });
    }

  } catch (error) {
    console.error('Health check error:', error);
    return NextResponse.json({
      success: false,
      frontend: 'error',
      error: 'Health check failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  // Allow POST for testing
  return GET(req);
}