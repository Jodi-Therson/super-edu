# rag_engine.py
import faiss
import numpy as np
import pickle
import os
import google.generativeai as genai
from dotenv import load_dotenv
import mimetypes

# Load environment variables to configure the API key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")
genai.configure(api_key=api_key)

class RAGQueryEngine:
    def __init__(self, 
                 index_path="index/my_faiss_index.index", 
                 docs_path="index/documents.pkl"):
        
        print("⏳ Loading RAG engine...")
        try:
            self.index = faiss.read_index(index_path)
            with open(docs_path, "rb") as f:
                self.documents = pickle.load(f)
        except FileNotFoundError as e:
            print("❌ Error: Could not find index or document files.")
            print("Please run 'build_index.py' first.")
            raise e
            
        self.embedding_model = 'models/text-embedding-004'
        self.llm = genai.GenerativeModel('gemini-2.0-flash') 
        
        # Inisialisasi riwayat percakapan
        self.history = []
        print(f"✅ RAG Engine Ready. Loaded {self.index.ntotal} document vectors.")

    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        # ... (fungsi ini tidak berubah) ...
        query_embedding = genai.embed_content(
            model=self.embedding_model,
            content=query,
            task_type="RETRIEVAL_QUERY"
        )['embedding']
        
        _distances, indices = self.index.search(np.array([query_embedding]), top_k)
        retrieved_docs = [self.documents[i] for i in indices[0]]
        return "\n---\n".join(retrieved_docs)

    def reset_chat(self):
        """Mereset atau menghapus riwayat percakapan."""
        self.history = []
        print("🧹 Riwayat percakapan telah direset.")

    def ask(self, query: str, image_data=None, audio_file_path=None):
        """
        Mengajukan pertanyaan ke sistem RAG dengan dukungan input multimodal.
        - image_data: bytes dari file gambar.
        - audio_file_path: path sementara ke file audio yang diunggah.
        """
        retrieved_context = self.retrieve_context(query)
        conversation_history = "\n".join(self.history)

        image_instruction = "Analisis juga GAMBAR yang dilampirkan sebagai bagian utama dari jawaban Anda. " if image_data else ""
        
        # Prompt untuk memeriksa relevansi konteks
        relevance_check_prompt = f"""
        Analisis Pertanyaan dan Konteks berikut. Apakah Konteks ini relevan untuk menjawab Pertanyaan tersebut?
        Jawab hanya dengan 'YA' atau 'TIDAK'.

        Pertanyaan: "{query}"

        Konteks:
        "{retrieved_context}"
        """
        
        try:
            relevance_response = self.llm.generate_content(relevance_check_prompt)
            is_relevant = 'YA' in relevance_response.text.upper()
        except Exception as e:
            print(f"Error saat memeriksa relevansi: {e}")
            is_relevant = False

        # Logika untuk memilih prompt berdasarkan relevansi
        if is_relevant:
            source = "konteks"
            final_prompt = f"""
            Anda adalah seorang tutor AI yang cerdas dan dapat diandalkan. {image_instruction}
            Tugas utama Anda adalah menjawab pertanyaan pengguna **hanya berdasarkan Konteks** yang tersedia di bawah ini. Jangan gunakan pengetahuan dari luar konteks ini.

            **Aturan Penting:**
            1.  **Sebutkan Sumber:** Selalu awali jawaban Anda dengan kalimat: "Berdasarkan informasi yang saya punya,..."
            2.  **Metode Mengajar:** Jangan langsung memberikan jawaban akhir. Bimbing pengguna untuk memahami informasi dari konteks secara bertahap. Jelaskan konsepnya seolah-olah Anda adalah seorang guru.
            3.  **Singkat dan Jelas:** Batasi penjelasan Anda agar tidak lebih dari 10 kalimat untuk menjaga agar tetap ringkas.

            Gunakan Riwayat Percakapan untuk menjaga alur diskusi yang relevan.

            ---
            Riwayat Percakapan:
            {conversation_history}
            ---
            Konteks:
            {retrieved_context}
            ---
            Pertanyaan Baru: {query}

            Panduan Anda (Ingat, mulai dengan menyebutkan sumber dari dokumen):
            """
        else:
            source = "umum"
            final_prompt = f"""
            Anda adalah seorang tutor AI yang sabar dan suportif. {image_instruction}
            Karena konteks spesifik tidak ditemukan, gunakan pengetahuan umum Anda untuk menjawab. Fokus utama Anda adalah pada **metode penyelesaian**, bukan memberikan jawaban instan.

            **Aturan Mengajar dan Interaksi Anda:**

            1.  **Mulai dengan Mengajak:** Selalu mulai dengan meminta pengguna untuk mencoba menjawab atau menguraikan pemikiran mereka terlebih dahulu. ("Coba kamu kerjakan dulu, nanti kita lihat bersama-sama.")

            2.  **Evaluasi Jawaban Pengguna:** Setelah pengguna memberikan jawaban, evaluasi dengan aturan berikut:
                * **Jika Jawaban Benar:** Berikan konfirmasi positif. ("Tepat sekali! Jawabanmu sudah benar.") Lalu tanyakan apakah ada soal lain.
                * **Jika Jawaban Kurang Tepat (Hampir Benar):** Apresiasi usaha mereka, lalu berikan koreksi atau tambahan informasi untuk melengkapi jawabannya. ("Sudah sangat bagus! Kamu hanya perlu menambahkan sedikit detail tentang...")
                * **Jika Jawaban Salah (Pertanyaan Umum/Non-Matematika):** Jelaskan mengapa jawaban itu kurang tepat dan berikan fakta yang benar dengan ramah.
                * **Jika Jawaban Salah (Pertanyaan Matematika):** Jangan langsung beri jawaban. Bimbing dengan memberikan petunjuk, rumus, atau langkah pengerjaan.

            3.  **Batas Maksimal 3 Kali Bimbingan:**
                * Untuk satu pertanyaan yang sama, Anda hanya boleh memberikan petunjuk atau bimbingan **maksimal 3 kali**.
                * Jika setelah bimbingan ketiga pengguna **masih memberikan jawaban yang salah**, jangan bertanya lagi. **Langsung berikan jawaban singkat yang benar**. Contoh: "Oke, terima kasih sudah mencoba. Jawaban yang tepat adalah 45. Ini didapat dari 5 dikali 9."

            4.  **Jaga Agar Tetap Ringkas:** Jaga agar setiap respons Anda tidak lebih dari 10 kalimat.

            Gunakan Riwayat Percakapan untuk memahami progres belajar pengguna.

            ---
            Riwayat Percakapan:
            {conversation_history}
            ---
            Pertanyaan Baru: {query}

            Panduan Anda (Ingat, ajak pengguna untuk mencoba dahulu dan ikuti aturan interaksi di atas):
            """

        # --- BAGIAN BARU: Membangun list konten untuk model multimodal ---
        content_parts = []
        
        # 1. Tambahkan data gambar jika ada
        if image_data:
            # Tipe mime bisa dideteksi atau di-hardcode jika Anda hanya mengizinkan satu jenis
            image_mime_type = "image/jpeg" 
            content_parts.append({"mime_type": image_mime_type, "data": image_data})

        # 2. Tambahkan data audio jika ada (melalui File API)
        if audio_file_path:
            print(f"Mengunggah file audio: {audio_file_path}")
            audio_file = genai.upload_file(path=audio_file_path)
            content_parts.append(audio_file)

        # 3. Tambahkan prompt teks utama di akhir
        content_parts.append(final_prompt)
        
        try:
            # Gunakan 'content_parts' sebagai input
            response = self.llm.generate_content(content_parts)
            answer = response.text

            # Tambahkan interaksi ke riwayat (hanya teksnya)
            self.history.append(f"Pengguna: {query}")
            self.history.append(f"Tutor: {answer}")

            return {"answer": answer, "source": source}
        except Exception as e:
            print(f"Error saat membuat respons multimodal: {e}")
            return {"answer": "Maaf, terjadi kesalahan saat memproses permintaan Anda.", "source": "error"}