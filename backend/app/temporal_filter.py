import numpy as np
import cv2


class TemporalFilter:
   
    def __init__(self, alpha=0.7):

        # Alpha değerini 0-1 aralığında sınırlandır
        self.alpha = max(0.0, min(1.0, alpha))
        
        # Önceki sonucu saklayacak değişken
        self.previous_frame = None
        
        # İstatistikler (performans takibi için)
        self.frame_count = 0
        self.filter_enabled = True
        
    def update(self, new_frame):

        
       
        if new_frame is None:
            print("Warning: new_frame is empty (None), filter skipped.")
            return None
        
        self.frame_count += 1
        
        
        # Eğer daha önce hiç kare yoksa, doğrudan yeni kareyi kullan
        if self.previous_frame is None:
            self.previous_frame = new_frame.copy()  
            return self.previous_frame
        
        # ----- 3. Filtre devre dışıysa veya alpha=1.0 ise direkt yeni kareyi döndür -----
        if not self.filter_enabled or self.alpha >= 0.99:
            self.previous_frame = new_frame.copy()
            return self.previous_frame
        
       
        # Eğer boyutlar farklıysa, önceki kareyi yeniden boyutlandır
        if new_frame.shape != self.previous_frame.shape:
            print(f"Warning: Dimension mismatch! new: {new_frame.shape}, prev: {self.previous_frame.shape}")
            print("Previous frame is being resized...")
            self.previous_frame = cv2.resize(
                self.previous_frame, 
                (new_frame.shape[1], new_frame.shape[0])
            )
        
        
        beta = 1.0 - self.alpha
        
        filtered_frame = cv2.addWeighted(
            new_frame,           # src1: yeni kare (ağırlık = alpha)
            self.alpha,          # alpha: yeni karenin ağırlığı
            self.previous_frame, # src2: önceki sonuç (ağırlık = beta)
            beta,                # beta: eski karenin ağırlığı
            0.0                  # gamma: toplama sabiti (genelde 0)
        )
        
        # ----- 6. Sonucu kaydet (bir sonraki çağrı için) -----
        self.previous_frame = filtered_frame.copy()
        
        return filtered_frame
    
    def reset(self):

        self.previous_frame = None
        self.frame_count = 0
        print("Temporal filter resetted.")
    
    def set_alpha(self, alpha):
   
        self.alpha = max(0.0, min(1.0, alpha))
        print(f"Alpha value updated: {self.alpha:.2f}")
    
    def enable(self):
        self.filter_enabled = True
        print("Temporal filter activated.")
    
    def disable(self):
        self.filter_enabled = False
        print("Temporal filter disabled.")
    
    def get_stats(self):

        return {
            "frame_count": self.frame_count,
            "alpha": self.alpha,
            "filter_enabled": self.filter_enabled,
            "has_previous": self.previous_frame is not None
        }




class AdaptiveTemporalFilter(TemporalFilter):
    """
    Hareket miktarına göre alpha değerini ayarlayan adaptif filtre.
    
    Çok hareketli sahnelerde alpha artar (daha az filtre, daha az gölgelenme)
    Az hareketli sahnelerde alpha azalır (daha çok filtre, daha yumuşak geçiş)
    """
    
    def __init__(self, alpha=0.7, motion_sensitivity=0.1):
   
        super().__init__(alpha)
        self.motion_sensitivity = motion_sensitivity
        self.previous_gray = None
        
    def update(self, new_frame):

        if new_frame is None:
            return None
            
        gray = cv2.cvtColor(new_frame, cv2.COLOR_BGR2GRAY)
        
        if self.previous_gray is not None:
            diff = cv2.absdiff(self.previous_gray, gray)
            motion_amount = np.mean(diff) / 255.0  # 0-1 arası normalize et
            
            adaptive_alpha = self.alpha + (motion_amount * self.motion_sensitivity)
            adaptive_alpha = max(0.3, min(0.95, adaptive_alpha))  # Sınırlandır
            
            original_alpha = self.alpha
            self.alpha = adaptive_alpha
            
            result = super().update(new_frame)
            
            self.alpha = original_alpha
            
        else:
            result = super().update(new_frame)
        
        # Önceki kareyi kaydet
        self.previous_gray = gray
        
        return result


# Gelişmiş Temporal Filtre: Optik Akış Tabanlı

class OpticalFlowFilter:
    
    
    def __init__(self, alpha=0.7, flow_method='farneback', 
                 pyr_scale=0.5, levels=3, winsize=15, iterations=3):
        
        self.alpha = max(0.0, min(1.0, alpha))
        self.flow_method = flow_method
        
        # Farneback parametreleri
        self.pyr_scale = pyr_scale
        self.levels = levels
        self.winsize = winsize
        self.iterations = iterations
        
        # Lucas-Kanade parametreleri
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # Önceki frame'leri sakla
        self.previous_styled = None
        self.previous_gray = None
        
        # İstatistikler
        self.frame_count = 0
        self.filter_enabled = True
        
    def compute_farneback_flow(self, prev_gray, curr_gray):
       
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray,
            None,
            self.pyr_scale,
            self.levels,
            self.winsize,
            self.iterations,
            7,      # poly_n
            1.5,    # poly_sigma
            0       # flags
        )
        return flow
    
    def compute_lucas_kanade_flow(self, prev_gray, curr_gray):
      
        # Önceki karedeki köşe noktalarını bul
        prev_points = cv2.goodFeaturesToTrack(
            prev_gray, maxCorners=500, qualityLevel=0.01, 
            minDistance=10, blockSize=3
        )
        
        if prev_points is None or len(prev_points) < 10:
            return None
        
        # Yeni karedeki noktaları hesapla
        curr_points, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, curr_gray, prev_points, None, **self.lk_params
        )
        
        # Başarılı eşleşmeleri filtrele
        good_prev = prev_points[status == 1]
        good_curr = curr_points[status == 1]
        
        if len(good_prev) < 4:
            return None
        
        # Homografi matrisi hesapla (projective transform)
        H, _ = cv2.findHomography(good_prev, good_curr, cv2.RANSAC, 5.0)
        
        return H
    
    def warp_frame_with_flow(self, frame, flow):
       
      
        h, w = frame.shape[:2]
        
        # Grid oluştur (her pikselin koordinatları)
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        
        # Akış vektörlerini uygula
        map_x = (grid_x + flow[..., 0]).astype(np.float32)
        map_y = (grid_y + flow[..., 1]).astype(np.float32)
        
        # Sınırları kontrol et (görüntü dışına taşmayı önle)
        map_x = np.clip(map_x, 0, w - 1)
        map_y = np.clip(map_y, 0, h - 1)
        
        # Remap ile warp işlemi
        warped = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        
        return warped
    
    def warp_frame_with_homography(self, frame, H):
        
        h, w = frame.shape[:2]
        warped = cv2.warpPerspective(frame, H, (w, h))
        return warped
    
    def update(self, new_styled_frame, original_frame=None):
        
        
        # ----- 1. Girdi kontrolü -----
        if new_styled_frame is None:
            return None
        
        self.frame_count += 1
        
        # ----- 2. İlk kare özel durumu -----
        if self.previous_styled is None:
            self.previous_styled = new_styled_frame.copy()
            
            # Orijinal frame varsa gri tona çevir
            if original_frame is not None:
                self.previous_gray = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
            else:
                self.previous_gray = cv2.cvtColor(new_styled_frame, cv2.COLOR_BGR2GRAY)
            
            return new_styled_frame
        
        # ----- 3. Filtre devre dışıysa -----
        if not self.filter_enabled or self.alpha >= 0.99:
            self.previous_styled = new_styled_frame.copy()
            return new_styled_frame
        
        # ----- 4. Optik akış hesaplamak için referans frame'leri hazırla -----
        if original_frame is not None:
            # Orijinal frame'leri kullan (daha doğru akış)
            curr_gray = cv2.cvtColor(original_frame, cv2.COLOR_BGR2GRAY)
            use_styled_for_flow = False
        else:
            # Stilize frame'leri kullan (daha az doğru ama her zaman çalışır)
            curr_gray = cv2.cvtColor(new_styled_frame, cv2.COLOR_BGR2GRAY)
            use_styled_for_flow = True
        
        # ----- 5. Optik akış hesapla -----
        warped_previous = None
        
        if self.flow_method == 'farneback':
            # Yoğun optik akış hesapla
            flow = self.compute_farneback_flow(self.previous_gray, curr_gray)
            
            if flow is not None:
                # Önceki stilize kareyi hareket vektörlerine göre warp et
                warped_previous = self.warp_frame_with_flow(self.previous_styled, flow)
        
        elif self.flow_method == 'lucas_kanade':
            # Homografi matrisi hesapla
            H = self.compute_lucas_kanade_flow(self.previous_gray, curr_gray)
            
            if H is not None:
                warped_previous = self.warp_frame_with_homography(self.previous_styled, H)
        
        # ----- 6. Warp başarısız olduysa basit hareketli ortalama kullan -----
        if warped_previous is None:
            # Fallback: basit hareketli ortalama
            beta = 1.0 - self.alpha
            filtered_frame = cv2.addWeighted(new_styled_frame, self.alpha,
                                             self.previous_styled, beta, 0)
        else:
            # Warp edilmiş kare ile yeni kareyi birleştir
            beta = 1.0 - self.alpha
            filtered_frame = cv2.addWeighted(new_styled_frame, self.alpha,
                                             warped_previous, beta, 0)
        
        # ----- 7. Sonuçları kaydet (bir sonraki çağrı için) -----
        self.previous_styled = filtered_frame.copy()
        self.previous_gray = curr_gray.copy()
        
        return filtered_frame
    
    def reset(self):
        """Filtreyi sıfırlar (yeni video için)."""
        self.previous_styled = None
        self.previous_gray = None
        self.frame_count = 0
        print("Optical flow filter reset..")
    
    def set_alpha(self, alpha):
        """Alpha değerini günceller."""
        self.alpha = max(0.0, min(1.0, alpha))
        print(f"Optical flow filter alpha: {self.alpha:.2f}")
    
    def enable(self):
        """Filtreyi aktif eder."""
        self.filter_enabled = True
        print("Optical flow filter active.")
    
    def disable(self):
        """Filtreyi devre dışı bırakır."""
        self.filter_enabled = False
        print("Optical flow filter disabled.")
    
    def get_stats(self):
        """Filtre istatistiklerini döndürür."""
        return {
            "frame_count": self.frame_count,
            "alpha": self.alpha,
            "filter_enabled": self.filter_enabled,
            "flow_method": self.flow_method,
            "has_previous": self.previous_styled is not None
        }



# Hızlı Optik Akış Filtresi (Lightweight versiyon)

class LightweightOpticalFlowFilter(OpticalFlowFilter):
    """
    Daha hızlı çalışan, optimize edilmiş optik akış filtresi.
    Kaliteyi biraz azaltarak hızı artırır.
    """
    
    def __init__(self, alpha=0.7):
        """
        Hızlı optik akış filtresi.
        Farneback parametreleri daha düşük kalite için optimize edilmiştir.
        """
        super().__init__(
            alpha=alpha,
            flow_method='farneback',
            pyr_scale=0.5,
            levels=2,      # Daha az seviye
            winsize=9,     # Daha küçük pencere
            iterations=2   # Daha az yineleme
        )
        print("fast optical flow filter started.")



def test_temporal_filter():

    import time
    
    print("="*50)
    print("Temporal Filtre Test")
    print("="*50)
    
    # 1. Filtreyi oluştur
    print("\n1. TemporalFilter is created (alpha=0.7)...")
    filter = TemporalFilter(alpha=0.7)
    
    # 2. Test görüntüleri oluştur (rastgele renklerde kareler)
    print("\n2. Test frames are generated (10 random color frames)...")
    
    # Boyut: 480x640, 3 kanal (BGR)
    height, width = 480, 640
    
    frames = []
    for i in range(10):
        # Rastgele renklerde kareler
        random_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        frames.append(random_frame)
    
    # 3. Filtreyi uygula
    print("\n3. Filter is applied to each frame...")
    
    for i, frame in enumerate(frames):
        # Filtrelenmiş kare
        filtered = filter.update(frame)
        
        # İstatistikleri göster
        stats = filter.get_stats()
        print(f"   Frame {i+1}: frame_count={stats['frame_count']}, alpha={stats['alpha']:.2f}")
        
        # İlk ve son kare arasındaki farkı hesapla
        if i == 0:
            print(f"      First frame: colors are random, no previous frame to compare.")
        elif i == len(frames)-1:
            diff = np.mean(np.abs(frame.astype(float) - filtered.astype(float)))
            print(f"      Last frame: Filtered vs original= {diff:.2f} (less diff means more smoothing)")
    
    # 4. Filtre istatistiklerini göster
    print("\n4. Filter statistics:")
    stats = filter.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 5. Filtreyi sıfırla
    print("\n5. Filter is reset...")
    filter.reset()
    
    print("\n" + "="*50)
    print("TEST SUCCEEDED!")
    print("="*50)


# Eğer bu dosya doğrudan çalıştırılırsa test fonksiyonunu çalıştır
if __name__ == "__main__":
    test_temporal_filter()