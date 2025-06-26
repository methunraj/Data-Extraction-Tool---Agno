import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { backendAIService } from '@/services/backend-api';

interface AgentStatus {
  [key: string]: any;
}

export const AgentMonitor = () => {
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgentStatus = async () => {
      try {
        setLoading(true);
        const status = await backendAIService.getAgentPoolStatus();
        setAgentStatus(status);
        setError(null);
      } catch (err) {
        setError('Failed to fetch agent status.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAgentStatus();
    const interval = setInterval(fetchAgentStatus, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Pool Status</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && <p>Loading...</p>}
        {error && <p className="text-red-500">{error}</p>}
        {agentStatus && (
          <div className="space-y-2">
            <p><strong>Model:</strong> {agentStatus.model_id}</p>
            <p><strong>Max Agents:</strong> {agentStatus.max_agents}</p>
            <p><strong>Active Agents:</strong> {agentStatus.current_agents}</p>
            <div>
              <strong>Cached Agent Types:</strong>
              <ul className="list-disc pl-5">
                {agentStatus.cached_agent_types.map((type: string) => (
                  <li key={type}>{type}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};