import cv2
import numpy as np
from sklearn.linear_model import LogisticRegression
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

class BASMEDSecure:
    def __init__(self):

        self.model = LogisticRegression(max_iter=1500, multi_class='multinomial')
        self.is_trained = False
        
    def _create_deterministic_labels(self, pixel_values: np.ndarray) -> np.ndarray:
        labels = np.zeros_like(pixel_values, dtype=int)
        labels[(pixel_values >= 101) & (pixel_values <= 150)] = 1
        labels[pixel_values >= 151] = 2
        return labels

    def train_model(self, image_gray: np.ndarray):
        flat_pixels = image_gray.flatten().reshape(-1, 1)
        labels = self._create_deterministic_labels(flat_pixels).flatten()
        
        print(f"Memulai inisialisasi pelatihan model ML pada {len(flat_pixels)} entri piksel...")
        self.model.fit(flat_pixels, labels)
        self.is_trained = True
        print("Pelatihan Model Regresi Logistik selesai secara operasional.")

    def _get_secret_bits(self, data_bytes: bytes) -> str:
        return ''.join(format(byte, '08b') for byte in data_bytes)

    def _bits_to_bytes(self, bit_string: str) -> bytes:
        byte_array = bytearray()
        for i in range(0, len(bit_string), 8):
            byte_str = bit_string[i:i+8]
            if len(byte_str) == 8:
                byte_array.append(int(byte_str, 2))
        return bytes(byte_array)

    def embed_data(self, cover_image: np.ndarray, secret_data: bytes):
        if not self.is_trained:
            self.train_model(cover_image)

        secret_bits = self._get_secret_bits(secret_data)
        secret_len = len(secret_bits)
        
        flat_image = cover_image.flatten()
        predicted_labels = self.model.predict(flat_image.reshape(-1, 1))
        
        P0 = np.sum(predicted_labels == 0)
        P1 = np.sum(predicted_labels == 1)
        P2 = np.sum(predicted_labels == 2)
        
        max_capacity = (3 * P0) + (2 * P1) + (1 * P2)
        if secret_len > max_capacity:
            raise ValueError(f"Overload: Ukuran payload ({secret_len} bit) melampaui "
                             f"Kapasitas Penyerapan Maksimal ({max_capacity} bit).")

        stego_pixels = flat_image.copy()
        
        case_type = 0
        if secret_len <= P0:
            case_type = 1
        elif secret_len <= (2 * P0 + P1):
            case_type = 2
        else:
            case_type = 3

        print(f"Operasi Penyisipan Bekerja dalam Skenario Kategori: Kasus {case_type}")

        bit_index = 0
        pixel_index = 0
        key_array = {}
        
        while bit_index < secret_len:
            if pixel_index >= len(stego_pixels):
                break
                
            label = predicted_labels[pixel_index]
            pixel_val = stego_pixels[pixel_index]
            bits_to_embed = 0
            
            if case_type == 1:
                if label == 0:
                    bits_to_embed = 1
            elif case_type == 2:
                if label == 0:
                    bits_to_embed = 2
                elif label == 1:
                    bits_to_embed = 1
            elif case_type == 3:
                if label == 0:
                    bits_to_embed = 3
                elif label == 1:
                    bits_to_embed = 2
                elif label == 2:
                    bits_to_embed = 1

            bits_to_embed = min(bits_to_embed, secret_len - bit_index)

            if bits_to_embed > 0:
                extracted_bits = secret_bits[bit_index : bit_index + bits_to_embed]
                pixel_val_cleared = pixel_val & ~((1 << bits_to_embed) - 1)
                pixel_val_new = pixel_val_cleared | int(extracted_bits, 2)
                stego_pixels[pixel_index] = pixel_val_new
                
                key_array.append(bits_to_embed)
                bit_index += bits_to_embed
            else:
                key_array.append(0) 

            pixel_index += 1

        stego_image = stego_pixels.reshape(cover_image.shape)
        return stego_image, key_array

    def extract_data(self, stego_image: np.ndarray, key_array: list) -> bytes:
        if not self.is_trained:
            self.train_model(stego_image) 
        
        flat_stego = stego_image.flatten()
        _ = self.model.predict(flat_stego.reshape(-1, 1)) # Dummy inference
        
        secret_bits_extracted = ""
        pixel_index = 0
        
        for key_val in key_array:
            if key_val > 0:
                pixel_val = flat_stego[pixel_index]
                extracted_int = pixel_val & ((1 << key_val) - 1)
                
                bin_format = f"0{key_val}b"
                extracted_bits = format(extracted_int, bin_format)
                secret_bits_extracted += extracted_bits
            pixel_index += 1

        return self._bits_to_bytes(secret_bits_extracted)

    def evaluate_performance(self, cover_img: np.ndarray, stego_img: np.ndarray):
        data_range = 255
        psnr_val = psnr(cover_img, stego_img, data_range=data_range)
        ssim_val = ssim(cover_img, stego_img, data_range=data_range)
        return psnr_val, ssim_val

if __name__ == "__main__":
    np.random.seed(99)
    simulated_cover_dicom = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
    
    secret_record = (b"METADATA DICOM RAHASIA | PASIEN: A.N. MISTER X | "
                     b"DIAGNOSA: INFILTRASI KARSINOMA PARU LOBUS KANAN TAHAP III | "
                     b"INSTRUKSI TERAPI: PROTOKOL KEMOTERAPI AGRESIF " * 100)
    basmed_controller = BASMEDSecure()
    
    stego_matrix, stego_keys = basmed_controller.embed_data(simulated_cover_dicom, secret_record)
    val_psnr, val_ssim = basmed_controller.evaluate_performance(simulated_cover_dicom, stego_matrix)
    
    print("\n--- LAPORAN HASIL PENYISIPAN ---")
    print(f"Data berhasil dilestarikan. Kapasitas Kunci Peta mencapai: {len(stego_keys)} indeks terakumulasi.")
    print(f"[+] Evaluasi Degradasi Kuantitatif - PSNR : {val_psnr:.3f} dB")
    print(f"[+] Evaluasi Degradasi Kuantitatif - SSIM : {val_ssim:.5f}")
    
    recovered_data = basmed_controller.extract_data(stego_matrix, stego_keys)
    print("\n--- LAPORAN HASIL EKSTRAKSI ---")
    
    try:
        decoded_text = recovered_data.decode('utf-8')
        print(f"[+] Sampel Teks Rekam Medis (Dipotong): {decoded_text[:100]}...")
        if secret_record == recovered_data:
            print("[+] Verifikasi Integritas Data Biner: SUKSES (100% Cocok)")
        else:
            print("[!] Peringatan: Kerusakan struktur data sewaktu rekonstitusi.")
    except Exception as e:
        print(f"[!] Kegagalan transkripsi pemulihan teks: {e}")