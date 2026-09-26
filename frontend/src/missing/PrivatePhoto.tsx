import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Platform, StyleSheet, Text, View } from 'react-native';
import { theme } from '../theme';
import { photoRequest, photoUrl } from './support';

export function PrivatePhoto({ draftId, id, token }: { draftId: string; id: string; token: string }) {
  const [uri, setUri] = useState('');
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true; let blobUrl = '';
    if (Platform.OS !== 'web') { setUri(photoUrl(draftId, id)); return; }
    photoRequest(draftId, token, id).then(r => r.blob()).then(blob => {
      if (!active) return;
      blobUrl = URL.createObjectURL(blob); setUri(blobUrl);
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [draftId, id, token]);
  return <View style={styles.frame}>
    {error ? <Text testID={`missing-photo-error-${id}`} style={styles.error}>Preview unavailable</Text> : uri ? <Image testID={`missing-photo-${id}`} source={{ uri, headers: { Authorization: `Bearer ${token}` } }} style={styles.image} resizeMode="contain" onError={() => setError(true)} /> : <ActivityIndicator testID={`missing-photo-loading-${id}`} color={theme.colors.primary} />}
  </View>;
}
const styles = StyleSheet.create({ frame: { height: 160, backgroundColor: theme.colors.surfaceSecondary, borderRadius: 12, justifyContent: 'center', overflow: 'hidden' }, image: { width: '100%', height: '100%' }, error: { color: theme.colors.error, textAlign: 'center' } });