'use client';

import { useState, useEffect } from 'react';

export interface ServiceHealth {
  name: string;
  label: string;
  icon: string;
  color: string;
  status: 'healthy' | 'degraded' | 'down' | 'unknown';
  responseTime?: number;
  lastChecked: number;
}

const SERVICES = [
  { name: 'cspm', label: 'CSPM', icon: 'CSPM', color: 'var(--accent)', port: 8006 },
  { name: 'cwpp', label: 'CWPP', icon: 'CWPP', color: 'var(--high)', port: 8014 },
  { name: 'ciem', label: 'CIEM', icon: 'CIEM', color: '#6b2fa0', port: 8013 },
  { name: 'kspm', label: 'KSPM', icon: 'KSPM', color: '#326ce5', port: 8016 },
  { name: 'dspm', label: 'DSPM', icon: 'DSPM', color: 'var(--success)', port: 8015 },
  { name: 'cdr', label: 'CDR', icon: 'CDR', color: 'var(--critical)', port: 8011 },
  { name: 'cicd', label: 'CI/CD', icon: 'CI/CD', color: 'var(--warning)', port: 8012 },
  { name: 'aiops', label: 'AIOps', icon: 'AIOps', color: 'var(--accent)', port: 8001 },
];

async function checkServiceHealth(service: typeof SERVICES[0]): Promise<ServiceHealth> {
  const startTime = Date.now();
  
  try {
    // Try to ping the service health endpoint
    const response = await fetch(`http://localhost:${service.port}/health`, {
      method: 'GET',
      timeout: 5000, // 5 second timeout
    });
    
    const responseTime = Date.now() - startTime;
    
    if (response.ok) {
      return {
        ...service,
        status: responseTime > 2000 ? 'degraded' : 'healthy',
        responseTime,
        lastChecked: Date.now(),
      };
    } else {
      return {
        ...service,
        status: 'down',
        responseTime,
        lastChecked: Date.now(),
      };
    }
  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.log(`Service ${service.name} health check failed:`, error);
    
    return {
      ...service,
      status: 'down',
      responseTime,
      lastChecked: Date.now(),
    };
  }
}

export function useServiceHealth() {
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<number>(0);

  const checkAllServices = async () => {
    setIsLoading(true);
    console.log('Checking health of all services...');
    
    try {
      const healthChecks = await Promise.all(
        SERVICES.map(service => checkServiceHealth(service))
      );
      
      console.log('Service health results:', healthChecks);
      setServices(healthChecks);
      setLastUpdate(Date.now());
    } catch (error) {
      console.error('Error checking service health:', error);
      // Fallback to unknown status for all services
      setServices(SERVICES.map(service => ({
        ...service,
        status: 'unknown' as const,
        lastChecked: Date.now(),
      })));
    } finally {
      setIsLoading(false);
    }
  };

  // Initial health check
  useEffect(() => {
    checkAllServices();
  }, []);

  // Periodic health checks every 30 seconds
  useEffect(() => {
    const interval = setInterval(checkAllServices, 30000);
    return () => clearInterval(interval);
  }, []);

  return {
    services,
    isLoading,
    lastUpdate,
    refetch: checkAllServices,
  };
}