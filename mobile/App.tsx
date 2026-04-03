import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StatusBar,
  Alert,
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  Animated,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { api, getServerUrl, setServerUrl } from './src/api';

const { width } = Dimensions.get('window');

// ── Color Palette ────────────────────────────────────
const C = {
  bg: '#0a0e1a',
  bgCard: '#1a1f35',
  bgInput: '#0d1225',
  border: '#2a3150',
  borderFocus: '#6366f1',
  textPrimary: '#f1f5f9',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  accent: '#6366f1',
  accentLight: '#818cf8',
  success: '#22c55e',
  danger: '#ef4444',
  warning: '#f59e0b',
};

// ── Types ────────────────────────────────────────────
type Tab = 'control' | 'groups' | 'comments' | 'logs' | 'settings';
type BotStatus = 'stopped' | 'running' | 'stopping';

interface StatusData {
  status: BotStatus;
  comment_count: number;
  total_groups: number;
  current_group: string;
}

export default function App() {
  const [tab, setTab] = useState<Tab>('control');
  const [status, setStatus] = useState<StatusData>({
    status: 'stopped', comment_count: 0, total_groups: 0, current_group: '',
  });
  const [groupUrls, setGroupUrls] = useState('');
  const [maxPosts, setMaxPosts] = useState('5');
  const [delay, setDelay] = useState('7');
  const [groups, setGroups] = useState('');
  const [comments, setComments] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  const [serverUrl, setServerUrlState] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [connected, setConnected] = useState(false);

  const logRef = useRef<ScrollView>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // ── Pulse animation for running status ──────────
  useEffect(() => {
    if (status.status === 'running') {
      const anim = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 0.3, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      );
      anim.start();
      return () => anim.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [status.status]);

  // ── Polling for status and logs ─────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      const data = await api.getLogs();
      if (data.logs) {
        setLogs(data.logs);
      }
    } catch { }
  }, []);

  useEffect(() => {
    getServerUrl().then(setServerUrlState);
    fetchStatus();
    pollRef.current = setInterval(() => {
      fetchStatus();
      if (tab === 'logs' || status.status === 'running') fetchLogs();
    }, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // ── Auto-scroll logs ───────────────────────────
  useEffect(() => {
    setTimeout(() => logRef.current?.scrollToEnd({ animated: true }), 100);
  }, [logs]);

  // ── Actions ────────────────────────────────────
  const handleStart = async () => {
    setLoading(true);
    try {
      const urls = groupUrls
        ? groupUrls.split('\n').map(u => u.trim()).filter(u => u)
        : [];
      const res = await api.startBot(urls, parseInt(maxPosts) || 5, parseInt(delay) || 7);
      if (res.error) {
        Alert.alert('Lỗi', res.error);
      } else {
        Alert.alert('Thành công', res.message);
        setTab('logs');
        fetchLogs();
      }
    } catch (e: any) {
      Alert.alert('Lỗi kết nối', 'Không kết nối được đến server.\nKiểm tra lại IP trong Settings.');
    }
    setLoading(false);
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const res = await api.stopBot();
      Alert.alert('Dừng bot', res.message || res.error);
    } catch {
      Alert.alert('Lỗi kết nối', 'Không gửi được lệnh dừng.');
    }
    setLoading(false);
  };

  const handleSaveGroups = async () => {
    setLoading(true);
    try {
      const list = groups.split('\n').map(g => g.trim()).filter(g => g);
      const res = await api.saveGroups(list);
      Alert.alert('✅', res.message);
    } catch { Alert.alert('Lỗi', 'Không lưu được.'); }
    setLoading(false);
  };

  const handleSaveComments = async () => {
    setLoading(true);
    try {
      const list = comments.split('\n').map(c => c.trim()).filter(c => c);
      const res = await api.saveComments(list);
      Alert.alert('✅', res.message);
    } catch { Alert.alert('Lỗi', 'Không lưu được.'); }
    setLoading(false);
  };

  const handleSaveServer = async () => {
    const url = serverUrl.trim().replace(/\/$/, '');
    if (!url) return Alert.alert('Lỗi', 'Nhập URL server!');
    await setServerUrl(url);
    setServerUrlState(url);
    fetchStatus();
    Alert.alert('✅', 'Đã lưu server URL!');
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchStatus();
    if (tab === 'groups') {
      try { const d = await api.getGroups(); setGroups((d.groups || []).join('\n')); } catch { }
    }
    if (tab === 'comments') {
      try { const d = await api.getComments(); setComments((d.comments || []).join('\n')); } catch { }
    }
    if (tab === 'logs') await fetchLogs();
    setRefreshing(false);
  };

  // Load data on tab switch
  useEffect(() => {
    if (tab === 'groups') {
      api.getGroups().then(d => setGroups((d.groups || []).join('\n'))).catch(() => { });
    }
    if (tab === 'comments') {
      api.getComments().then(d => setComments((d.comments || []).join('\n'))).catch(() => { });
    }
    if (tab === 'logs') fetchLogs();
  }, [tab]);

  // ── Render ─────────────────────────────────────
  const statusColor = status.status === 'running' ? C.success
    : status.status === 'stopping' ? C.warning : C.textMuted;
  const statusLabel = status.status === 'running' ? 'Đang chạy'
    : status.status === 'stopping' ? 'Đang dừng...' : 'Đã dừng';

  return (
    <View style={s.container}>
      <StatusBar barStyle="light-content" backgroundColor={C.bg} />

      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerIcon}>🤖</Text>
        <View>
          <Text style={s.headerTitle}>FB Auto Bot</Text>
          <View style={s.connRow}>
            <View style={[s.connDot, { backgroundColor: connected ? C.success : C.danger }]} />
            <Text style={s.connText}>{connected ? 'Đã kết nối' : 'Mất kết nối'}</Text>
          </View>
        </View>
      </View>

      {/* Status Cards */}
      <View style={s.statusBar}>
        <View style={s.statCard}>
          <Text style={s.statLabel}>TRẠNG THÁI</Text>
          <View style={s.statusRow}>
            <Animated.View style={[s.statusDot, { backgroundColor: statusColor, opacity: pulseAnim }]} />
            <Text style={[s.statValue, { fontSize: 13 }]}>{statusLabel}</Text>
          </View>
        </View>
        <View style={s.statCard}>
          <Text style={s.statLabel}>COMMENTS</Text>
          <Text style={s.statValue}>{status.comment_count}</Text>
        </View>
        <View style={s.statCard}>
          <Text style={s.statLabel}>NHÓM</Text>
          <Text style={s.statValue}>{status.total_groups}</Text>
        </View>
      </View>

      {/* Tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.tabBar}>
        {(['control', 'groups', 'comments', 'logs', 'settings'] as Tab[]).map(t => (
          <TouchableOpacity
            key={t}
            style={[s.tab, tab === t && s.tabActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[s.tabText, tab === t && s.tabTextActive]}>
              {t === 'control' ? '⚡ Điều khiển' :
                t === 'groups' ? '📋 Groups' :
                  t === 'comments' ? '💬 Comments' :
                    t === 'logs' ? '📊 Logs' : '⚙️ Settings'}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Content */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView
          style={s.content}
          contentContainerStyle={{ paddingBottom: 40 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.accent} />}
        >
          {/* ── Tab: Control ──────────── */}
          {tab === 'control' && (
            <View style={s.card}>
              <Text style={s.cardTitle}>⚡ Bảng điều khiển Bot</Text>

              <Text style={s.label}>URL Nhóm (mỗi dòng 1 URL)</Text>
              <TextInput
                style={[s.input, s.textarea]}
                multiline
                numberOfLines={4}
                value={groupUrls}
                onChangeText={setGroupUrls}
                placeholder="https://www.facebook.com/groups/..."
                placeholderTextColor={C.textMuted}
              />
              <Text style={s.hint}>Để trống sẽ dùng file groups.txt</Text>

              <View style={s.row}>
                <View style={{ flex: 1 }}>
                  <Text style={s.label}>Số bài / Nhóm</Text>
                  <TextInput
                    style={s.input}
                    value={maxPosts}
                    onChangeText={setMaxPosts}
                    keyboardType="numeric"
                    placeholderTextColor={C.textMuted}
                  />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={s.label}>Delay (giây)</Text>
                  <TextInput
                    style={s.input}
                    value={delay}
                    onChangeText={setDelay}
                    keyboardType="numeric"
                    placeholderTextColor={C.textMuted}
                  />
                </View>
              </View>

              <View style={s.btnGroup}>
                <TouchableOpacity
                  style={[s.btn, s.btnStart, status.status === 'running' && s.btnDisabled]}
                  onPress={handleStart}
                  disabled={status.status === 'running' || loading}
                >
                  {loading ? <ActivityIndicator color="#fff" size="small" /> :
                    <Text style={s.btnText}>▶ Bắt đầu chạy</Text>}
                </TouchableOpacity>
                <TouchableOpacity
                  style={[s.btn, s.btnStop, status.status !== 'running' && s.btnDisabled]}
                  onPress={handleStop}
                  disabled={status.status !== 'running' || loading}
                >
                  <Text style={s.btnText}>⏹ Dừng</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* ── Tab: Groups ───────────── */}
          {tab === 'groups' && (
            <View style={s.card}>
              <Text style={s.cardTitle}>📋 Quản lý Groups</Text>
              <Text style={s.label}>Mỗi dòng 1 URL nhóm</Text>
              <TextInput
                style={[s.input, s.textareaBig]}
                multiline
                value={groups}
                onChangeText={setGroups}
                placeholder="https://www.facebook.com/groups/..."
                placeholderTextColor={C.textMuted}
              />
              <TouchableOpacity style={[s.btn, s.btnSave]} onPress={handleSaveGroups}>
                <Text style={s.btnText}>💾 Lưu Groups</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* ── Tab: Comments ─────────── */}
          {tab === 'comments' && (
            <View style={s.card}>
              <Text style={s.cardTitle}>💬 Quản lý Comments</Text>
              <Text style={s.label}>Mỗi dòng 1 bình luận</Text>
              <TextInput
                style={[s.input, s.textareaBig]}
                multiline
                value={comments}
                onChangeText={setComments}
                placeholder="Nhập bình luận tại đây..."
                placeholderTextColor={C.textMuted}
              />
              <TouchableOpacity style={[s.btn, s.btnSave]} onPress={handleSaveComments}>
                <Text style={s.btnText}>💾 Lưu Comments</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* ── Tab: Logs ─────────────── */}
          {tab === 'logs' && (
            <View style={s.card}>
              <View style={s.logHeader}>
                <Text style={s.cardTitle}>📊 Realtime Logs</Text>
                <TouchableOpacity onPress={() => setLogs([])}>
                  <Text style={s.clearBtn}>Xoá</Text>
                </TouchableOpacity>
              </View>
              <ScrollView
                ref={logRef}
                style={s.logContainer}
                nestedScrollEnabled
              >
                {logs.length === 0 ? (
                  <Text style={s.logEmpty}>Chưa có log nào.</Text>
                ) : (
                  logs.map((log, i) => (
                    <Text
                      key={i}
                      style={[
                        s.logEntry,
                        log.includes('✅') && { color: C.success },
                        (log.includes('❌') || log.includes('Lỗi')) && { color: C.danger },
                        log.includes('⚠️') && { color: C.warning },
                      ]}
                    >
                      {log}
                    </Text>
                  ))
                )}
              </ScrollView>
            </View>
          )}

          {/* ── Tab: Settings ─────────── */}
          {tab === 'settings' && (
            <View style={s.card}>
              <Text style={s.cardTitle}>⚙️ Cài đặt Server</Text>
              <Text style={s.label}>Server URL</Text>
              <TextInput
                style={s.input}
                value={serverUrl}
                onChangeText={setServerUrlState}
                placeholder="http://192.168.1.100:5000"
                placeholderTextColor={C.textMuted}
                autoCapitalize="none"
                autoCorrect={false}
              />
              <Text style={s.hint}>
                Nhập IP máy tính chạy bot (cùng mạng WiFi).{'\n'}
                Ví dụ: http://192.168.1.100:5000
              </Text>
              <TouchableOpacity style={[s.btn, s.btnSave]} onPress={handleSaveServer}>
                <Text style={s.btnText}>💾 Lưu Server URL</Text>
              </TouchableOpacity>

              <View style={s.settingsInfo}>
                <Text style={s.settingsInfoTitle}>📱 Hướng dẫn kết nối</Text>
                <Text style={s.settingsInfoText}>
                  1. Chạy server trên máy tính: python server.py{'\n'}
                  2. Xem IP máy tính: ipconfig (Windows) / ifconfig (Mac/Linux){'\n'}
                  3. Nhập IP vào ô trên, port mặc định là 5000{'\n'}
                  4. Đảm bảo điện thoại và PC cùng WiFi
                </Text>
              </View>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────
const s = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: C.bg,
    paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight || 40 : 50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 16,
    gap: 14,
  },
  headerIcon: {
    fontSize: 36,
    width: 56,
    height: 56,
    lineHeight: 56,
    textAlign: 'center',
    backgroundColor: C.accent,
    borderRadius: 16,
    overflow: 'hidden',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: C.textPrimary,
    letterSpacing: -0.5,
  },
  connRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 2,
    gap: 6,
  },
  connDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  connText: {
    fontSize: 12,
    color: C.textMuted,
  },

  // Status Bar
  statusBar: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 8,
    marginBottom: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: C.bgCard,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 10,
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: C.textMuted,
    letterSpacing: 1,
    marginBottom: 4,
  },
  statValue: {
    fontSize: 22,
    fontWeight: '700',
    color: C.textPrimary,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },

  // Tabs
  tabBar: {
    flexGrow: 0,
    paddingHorizontal: 16,
    marginBottom: 10,
  },
  tab: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    marginRight: 6,
    backgroundColor: '#111827',
  },
  tabActive: {
    backgroundColor: C.accent,
  },
  tabText: {
    fontSize: 13,
    fontWeight: '500',
    color: C.textMuted,
  },
  tabTextActive: {
    color: '#fff',
    fontWeight: '600',
  },

  // Content
  content: {
    flex: 1,
    paddingHorizontal: 16,
  },
  card: {
    backgroundColor: C.bgCard,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: C.textPrimary,
    marginBottom: 16,
  },

  // Form
  label: {
    fontSize: 13,
    fontWeight: '500',
    color: C.textSecondary,
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: C.bgInput,
    borderWidth: 1.5,
    borderColor: C.border,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: C.textPrimary,
    fontSize: 14,
  },
  textarea: {
    minHeight: 90,
    textAlignVertical: 'top',
  },
  textareaBig: {
    minHeight: 200,
    textAlignVertical: 'top',
  },
  hint: {
    fontSize: 11,
    color: C.textMuted,
    marginTop: 4,
  },
  row: {
    flexDirection: 'row',
    marginTop: 4,
  },

  // Buttons
  btnGroup: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 24,
  },
  btn: {
    flex: 1,
    paddingVertical: 15,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnStart: {
    backgroundColor: C.success,
  },
  btnStop: {
    backgroundColor: C.danger,
  },
  btnSave: {
    backgroundColor: C.accent,
    marginTop: 16,
  },
  btnDisabled: {
    opacity: 0.35,
  },
  btnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },

  // Logs
  logHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  logContainer: {
    backgroundColor: C.bgInput,
    borderRadius: 10,
    padding: 12,
    maxHeight: 400,
  },
  logEntry: {
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 11,
    color: C.textSecondary,
    lineHeight: 18,
    marginBottom: 2,
  },
  logEmpty: {
    color: C.textMuted,
    textAlign: 'center',
    paddingVertical: 30,
    fontSize: 13,
  },
  clearBtn: {
    color: C.danger,
    fontSize: 13,
    fontWeight: '600',
  },

  // Settings
  settingsInfo: {
    marginTop: 24,
    backgroundColor: C.bgInput,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: C.border,
  },
  settingsInfoTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: C.textPrimary,
    marginBottom: 8,
  },
  settingsInfoText: {
    fontSize: 12,
    color: C.textSecondary,
    lineHeight: 20,
  },
});
