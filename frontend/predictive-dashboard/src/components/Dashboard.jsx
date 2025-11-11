import React, { useState, useEffect, useRef } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  Loader, 
  Activity, 
  TrendingUp, 
  AlertCircle,
  Zap,
  Thermometer,
  Gauge,
  RotateCcw,
  Server,
  Cpu,
  HardDrive,
  Network
} from 'lucide-react';

const API_URL = 'http://localhost:8080';
const WS_URL = 'ws://localhost:8080/ws';

const AlertModal = ({ alert, onAcknowledge }) => {
  if (!alert) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-linear-to-br from-red-500 to-red-600 text-white rounded-2xl shadow-2xl p-6 md:p-8 w-full max-w-md transform animate-pulse border border-red-300">
        <div className="flex flex-col items-center text-center">
          <div className="bg-white bg-opacity-20 p-3 rounded-full mb-4">
            <AlertTriangle className="w-12 h-12 text-red" />
          </div>
          <h2 className="text-2xl font-bold mb-2">CRITICAL ALERT</h2>
          <p className="text-lg mb-2 opacity-90">{alert.message}</p>
          <p className="text-sm opacity-80 mb-4">Probability: {(alert.probability * 100).toFixed(1)}%</p>
          <div className="grid grid-cols-2 gap-3 text-sm w-full mb-6 bg-white bg-opacity-10 p-3 rounded-lg">
            <div className="text-left">
              <p className="flex items-center"><Activity className="w-3 h-3 mr-1" /> Sensor A: {alert.sensor_readings?.sensor_A}</p>
              <p className="flex items-center"><AlertCircle className="w-3 h-3 mr-1" /> Errors: {alert.sensor_readings?.error_count}</p>
            </div>
            <div className="text-left">
              <p className="flex items-center"><Thermometer className="w-3 h-3 mr-1" /> Temp: {alert.sensor_readings?.temperature}°C</p>
              <p className="flex items-center"><Gauge className="w-3 h-3 mr-1" /> Vibration: {alert.sensor_readings?.vibration}</p>
            </div>
          </div>
          <button
            onClick={onAcknowledge}
            className="w-full bg-white text-red-600 py-3 rounded-xl hover:bg-gray-100 transition-all duration-200 shadow-lg font-semibold transform hover:scale-105"
          >
            ACKNOWLEDGE & DISMISS
          </button>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ icon, title, value, unit, trend, color = "blue", loading = false }) => (
  <div className={`bg-linear-to-br from-${color}-50 to-${color}-100 p-5 rounded-2xl shadow-lg border border-${color}-200 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1`}>
    <div className="flex items-center justify-between mb-3">
      <div className={`p-3 rounded-xl bg-${color}-500 bg-opacity-10`}>
        {React.cloneElement(icon, { className: `w-6 h-6 text-${color}-600` })}
      </div>
      <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
        trend === 'up' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
      }`}>
        {trend === 'up' ? '↑' : '↓'}
      </span>
    </div>
    <h3 className="text-sm font-medium text-gray-600 mb-2">{title}</h3>
    <div className="flex items-baseline">
      {loading ? (
        <Loader className="w-5 h-5 animate-spin text-gray-400" />
      ) : (
        <>
          <span className="text-2xl font-bold text-gray-900">{value}</span>
          {unit && <span className="text-sm text-gray-500 ml-1">{unit}</span>}
        </>
      )}
    </div>
  </div>
);

const RiskIndicator = ({ probability, loading = false }) => {
  const getRiskColor = (prob) => {
    if (prob > 0.7) return 'from-red-500 to-red-600';
    if (prob > 0.4) return 'from-yellow-500 to-yellow-600';
    return 'from-green-500 to-green-600';
  };

  const getRiskText = (prob) => {
    if (prob > 0.7) return 'HIGH RISK';
    if (prob > 0.4) return 'MEDIUM RISK';
    return 'LOW RISK';
  };

  const getIcon = (prob) => {
    if (prob > 0.7) return <AlertTriangle className="w-10 h-10 mr-3" />;
    if (prob > 0.4) return <AlertCircle className="w-10 h-10 mr-3" />;
    return <CheckCircle className="w-10 h-10 mr-3" />;
  };

  if (loading) {
    return (
      <div className="bg-linear-to-br from-gray-200 to-gray-300 rounded-2xl shadow-xl p-8 text-white transition-all duration-500 animate-pulse">
        <div className="flex items-center justify-center">
          <Loader className="w-8 h-8 animate-spin mr-3" />
          <span className="text-2xl font-extrabold">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-linear-to-br ${getRiskColor(probability)} rounded-2xl shadow-xl p-8 text-white transition-all duration-500 hover:shadow-2xl`}>
      <div className="flex items-center justify-center mb-6">
        {getIcon(probability)}
        <span className="text-3xl font-extrabold">{getRiskText(probability)}</span>
      </div>
      <div className="text-center">
        <p className="text-lg font-medium opacity-90 mb-3">Failure Probability</p>
        <p className="text-6xl font-extrabold mb-4">{(probability * 100).toFixed(1)}%</p>
      </div>
      <div className="w-full bg-white bg-opacity-30 rounded-full h-3">
        <div 
          className="bg-white h-3 rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${probability * 100}%` }}
        ></div>
      </div>
    </div>
  );
};

const App = () => {
  const [realTimeData, setRealTimeData] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [criticalAlert, setCriticalAlert] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const ws = useRef(null);

  // WebSocket connection for real-time data
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        setIsLoading(true);
        ws.current = new WebSocket(WS_URL);
        
        ws.current.onopen = () => {
          console.log('🔗 WebSocket connected');
          setConnectionStatus('connected');
          setIsLoading(false);
        };
        
        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLastUpdate(new Date());
            
            // Handle different message types from your backend
            if (data.predictions_made !== undefined) {
              // This is from your current backend format
              setRealTimeData({
                failure_probability: data.model_confidence ? 1 - data.model_confidence : 0.2,
                sensor_A: data.predictions_made,
                error_count: data.anomalies_detected || 0,
                temperature: data.system_load ? data.system_load * 100 : 45,
                vibration: data.throughput || 120,
                alert_level: data.anomalies_detected > 5 ? 'HIGH' : 'LOW'
              });
            } else if (data.type === 'realtime_update') {
              setRealTimeData(data);
            } else if (data.type === 'critical_alert') {
              setCriticalAlert(data);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        ws.current.onclose = () => {
          console.log('🔌 WebSocket disconnected');
          setConnectionStatus('disconnected');
          setIsLoading(false);
          setTimeout(connectWebSocket, 3000);
        };
        
        ws.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setConnectionStatus('error');
          setIsLoading(false);
        };
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setIsLoading(false);
      }
    };

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    connectWebSocket();

    // Simulate data if no WebSocket connection
    const fallbackData = setTimeout(() => {
      if (!realTimeData && connectionStatus === 'disconnected') {
        setRealTimeData({
          failure_probability: 0.15,
          sensor_A: 245,
          error_count: 2,
          temperature: 45,
          vibration: 120,
          alert_level: 'LOW'
        });
        setIsLoading(false);
      }
    }, 5000);

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      clearTimeout(fallbackData);
    };
  }, []);

  const handleAcknowledgeAlert = () => {
    setCriticalAlert(null);
  };

  const getSystemStatus = () => {
    if (isLoading) return 'Loading...';
    if (connectionStatus === 'connected') return 'All Systems Operational';
    if (connectionStatus === 'error') return 'Connection Issues';
    return 'Checking System Status';
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-900 via-purple-900 to-slate-900 p-4 md:p-8 font-sans">
      <AlertModal alert={criticalAlert} onAcknowledge={handleAcknowledgeAlert} />

      <div className="max-w-7xl mx-auto">
        {/* Enhanced Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 bg-linear-to-r from-blue-400 to-purple-400 bg-clip-text">
                Predictive Maintenance Dashboard
              </h1>
              <p className="text-gray-300 flex items-center">
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  connectionStatus === 'connected' ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                {getSystemStatus()}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center px-4 py-2 rounded-full text-sm font-semibold backdrop-blur-sm border ${
                connectionStatus === 'connected' 
                  ? 'bg-green-500 bg-opacity-20 text-green-300 border-green-400' 
                  : 'bg-red-500 bg-opacity-20 text-red-300 border-red-400'
              }`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  connectionStatus === 'connected' ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                {connectionStatus === 'connected' ? 'LIVE' : 'OFFLINE'}
              </div>
              {lastUpdate && (
                <div className="text-sm text-gray-400">
                  Last update: {lastUpdate.toLocaleTimeString()}
                </div>
              )}
              <button 
                onClick={() => window.location.reload()}
                className="p-2 bg-white bg-opacity-10 rounded-lg hover:bg-opacity-20 transition-all"
              >
                <RotateCcw className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>
        </header>

        {/* Real-time Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            icon={<Cpu className="w-6 h-6" />}
            title="CPU Usage"
            value={realTimeData?.sensor_A || 0}
            unit="units"
            trend="up"
            color="blue"
            loading={isLoading}
          />
          <MetricCard
            icon={<AlertCircle className="w-6 h-6" />}
            title="Error Count"
            value={realTimeData?.error_count || 0}
            unit="errors"
            trend="up"
            color="red"
            loading={isLoading}
          />
          <MetricCard
            icon={<Thermometer className="w-6 h-6" />}
            title="Temperature"
            value={realTimeData?.temperature || 0}
            unit="°C"
            trend="up"
            color="orange"
            loading={isLoading}
          />
          <MetricCard
            icon={<Gauge className="w-6 h-6" />}
            title="Throughput"
            value={realTimeData?.vibration || 0}
            unit="req/s"
            trend="down"
            color="purple"
            loading={isLoading}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Risk Assessment */}
            <div className="bg-white bg-opacity-5 backdrop-blur-sm rounded-2xl shadow-2xl border border-white border-opacity-10 p-6 hover:bg-opacity-10 transition-all duration-300">
              <h2 className="text-2xl font-semibold text-white mb-6 flex items-center">
                <Zap className="w-6 h-6 mr-2 text-yellow-400" />
                Real-time Risk Assessment
              </h2>
              <RiskIndicator 
                probability={realTimeData?.failure_probability || 0.1} 
                loading={isLoading}
              />
            </div>

            {/* System Status */}
            <div className="bg-white bg-opacity-5 backdrop-blur-sm rounded-2xl shadow-2xl border border-white border-opacity-10 p-6">
              <h2 className="text-2xl font-semibold text-white mb-6">System Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className={`p-4 rounded-xl backdrop-blur-sm border-2 transition-all ${
                  realTimeData?.alert_level === 'HIGH' 
                    ? 'bg-red-500 bg-opacity-20 border-red-400' 
                    : realTimeData?.alert_level === 'MEDIUM'
                    ? 'bg-yellow-500 bg-opacity-20 border-yellow-400'
                    : 'bg-green-500 bg-opacity-20 border-green-400'
                }`}>
                  <h3 className="font-semibold mb-2 text-white">Current Alert Level</h3>
                  <p className={`text-lg font-bold ${
                    realTimeData?.alert_level === 'HIGH' ? 'text-red-300' :
                    realTimeData?.alert_level === 'MEDIUM' ? 'text-yellow-300' :
                    'text-green-300'
                  }`}>
                    {realTimeData?.alert_level || 'NORMAL'}
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-blue-500 bg-opacity-20 border-2 border-blue-400 backdrop-blur-sm">
                  <h3 className="font-semibold mb-2 text-white">Recommendation</h3>
                  <p className="text-lg font-bold text-blue-300">
                    {realTimeData?.alert_level === 'HIGH' ? 'IMMEDIATE ACTION REQUIRED' :
                     realTimeData?.alert_level === 'MEDIUM' ? 'SCHEDULE INSPECTION' :
                     'NORMAL OPERATION'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-8">
            {/* Quick Actions */}
            <div className="bg-white bg-opacity-5 backdrop-blur-sm rounded-2xl shadow-2xl border border-white border-opacity-10 p-6">
              <h2 className="text-2xl font-semibold text-white mb-6">Quick Actions</h2>
              <div className="space-y-3">
                <button className="w-full bg-blue-500 bg-opacity-20 text-blue-300 py-3 rounded-xl hover:bg-opacity-30 transition-all duration-200 font-semibold border border-blue-400 backdrop-blur-sm transform hover:scale-105">
                  Generate Maintenance Report
                </button>
                <button className="w-full bg-green-500 bg-opacity-20 text-green-300 py-3 rounded-xl hover:bg-opacity-30 transition-all duration-200 font-semibold border border-green-400 backdrop-blur-sm transform hover:scale-105">
                  Schedule Inspection
                </button>
                <button className="w-full bg-purple-500 bg-opacity-20 text-purple-300 py-3 rounded-xl hover:bg-opacity-30 transition-all duration-200 font-semibold border border-purple-400 backdrop-blur-sm transform hover:scale-105">
                  View Historical Data
                </button>
              </div>
            </div>

            {/* Recent Alerts */}
            <div className="bg-white bg-opacity-5 backdrop-blur-sm rounded-2xl shadow-2xl border border-white border-opacity-10 p-6">
              <h2 className="text-2xl font-semibold text-white mb-6">Recent Activity</h2>
              <div className="space-y-3">
                {criticalAlert ? (
                  <div className="p-3 bg-red-500 bg-opacity-20 border border-red-400 rounded-lg backdrop-blur-sm">
                    <div className="flex items-center">
                      <AlertTriangle className="w-5 h-5 text-red-300 mr-2" />
                      <span className="font-semibold text-red-300">Critical Alert</span>
                    </div>
                    <p className="text-sm text-red-300 mt-1">High failure probability detected</p>
                  </div>
                ) : (
                  <div className="p-3 bg-green-500 bg-opacity-20 border border-green-400 rounded-lg backdrop-blur-sm">
                    <div className="flex items-center">
                      <CheckCircle className="w-5 h-5 text-green-300 mr-2" />
                      <span className="font-semibold text-green-300">All Systems Normal</span>
                    </div>
                    <p className="text-sm text-green-300 mt-1">No critical issues detected</p>
                  </div>
                )}
                <div className="p-3 bg-blue-500 bg-opacity-20 border border-blue-400 rounded-lg backdrop-blur-sm">
                  <div className="flex items-center">
                    <Activity className="w-5 h-5 text-blue-300 mr-2" />
                    <span className="font-semibold text-blue-300">Real-time Monitoring</span>
                  </div>
                  <p className="text-sm text-blue-300 mt-1">
                    {connectionStatus === 'connected' ? 'Live data streaming active' : 'Connecting to backend...'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;