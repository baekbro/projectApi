import os
from konlpy.tag import Kkma
from gensim.models import Word2Vec
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import pandas as pd
from MySQLDatabase import MySQLDatabase

class Nlp:
    
    def __init__(self):
        self.kkma = Kkma()  # Okt 인스턴스 생성
        self.model_path = "word2vec.model"
        self.model = None
        self.db = MySQLDatabase()
        # 기존 모델이 존재하면 로드
        if os.path.exists(self.model_path):
            self.model = Word2Vec.load(self.model_path)
    
    def KonlpyOkt(self, querys):
        """문장에서 명사만 추출하여 하나의 리스트로 반환 (한 글자 단어 제거)"""
        result = []
        for query in querys:
            if isinstance(query, str):
                nouns = self.kkma.nouns(query)
                filtered_noun = [word for word in nouns if len(word) > 1]
                if filtered_noun:
                    result.extend(filtered_noun)
        return result
    
    def CreateModel(self, querys):
        """Word2Vec 모델 학습 후 저장"""
        sentences = []
        for query in querys:
            if isinstance(query, str):
                # 각 query를 리스트로 감싸서 KonlpyOkt에 전달하면, 해당 문장에 대한 토큰 리스트를 얻을 수 있음
                tokens = self.KonlpyOkt([query])
                if tokens:  # 토큰이 존재할 경우에만 추가
                    sentences.append(tokens)
                    
        # sentences는 이제 각 문장의 토큰 리스트가 담긴 리스트임
        model = Word2Vec(sentences, vector_size=100, window=3, min_count=1, workers=4, sg=0)
        model.save(self.model_path)
        self.model = model  # 모델 업데이트
        print("✅ Word2Vec 모델이 성공적으로 학습되었습니다.")

    def train_book_model_and_get_tokens(self):
        """
        책 데이터를 이용하여 모델을 학습하고, 각 책의 description에서 KonlpyOkt 함수를 통해 
        단어 리스트를 추출하여 ISBN별로 매핑한 딕셔너리를 반환합니다.
        
        반환값: {isbn: tokens_list}
        """
        
        query = "SELECT books_isbn, books_description FROM tb_books"
        fetched_data_book = self.db.fetch_query(query=query)
        df_book = pd.DataFrame(fetched_data_book, columns=["books_isbn", "books_description"])
        print(df_book.info())
        
        # 모델 학습 (책의 description을 이용하여 Word2Vec 모델 생성)
        descriptions = df_book['books_description'].tolist()
        self.CreateModel(descriptions)
        
        isbn_tokens = {}
        for isbn, description in zip(df_book['books_isbn'], df_book['books_description']):
            tokens = self.KonlpyOkt([description])
            isbn_tokens[isbn] = tokens
            
        return isbn_tokens
    
    def ModelScore(self, word1, word2):
        """두 단어 간 유사도 계산"""
        if self.model is None:
            print("⚠️ 모델이 로드되지 않았습니다. 먼저 CreateModel을 실행하세요.")
            return
        
        if word1 in self.model.wv and word2 in self.model.wv:
            similarity = self.model.wv.similarity(word1, word2)
            print(f"🟢 '{word1}'과(와) '{word2}'의 유사도: {similarity:.4f}")
        else:
            print(f"⚠️ '{word1}' 또는 '{word2}'가 모델에 없습니다.")
    
    def SimilerWord(self, word):
        """특정 단어와 가장 유사한 단어 반환"""
        if self.model is None:
            print("⚠️ 모델이 로드되지 않았습니다. 먼저 CreateModel을 실행하세요.")
            return []

        if word in self.model.wv:
            similar_words = self.model.wv.most_similar(word, topn=2)
            result = [(similar_word, score) for similar_word, score in similar_words]  # ✅ 결과 저장
            return result  # ✅ 결과 반환
        else:
            print(f"⚠️ '{word}'가 모델에 없습니다.")
            return []

    def get_similar_keywords(self, newsData):
        """
        newsData의 각 키워드에 대해 가장 유사한 단어를 찾아 section별로 반환
        """
        similar_news_data = {}  # 최종 결과를 저장할 딕셔너리

        for section, keywords in newsData.items():
            similar_keywords = []
            
            for keyword in keywords:
                similar_words = self.SimilerWord(keyword)  # ✅ 유사한 단어 찾기
                
                # ✅ 유사한 단어가 있을 경우, 첫 번째 단어만 가져오기 (top1)
                if similar_words:
                    similar_keywords.append(similar_words[0][0])  # 단어만 저장
            
            # ✅ 결과 저장
            similar_news_data[section] = similar_keywords

        return similar_news_data  # ✅ section별 유사 키워드 반환

    def VisualizeModel(self, word_list=None):
        """Word2Vec 모델의 단어 벡터를 2D로 시각화"""
        
        if self.model is None:
            print("⚠️ 모델이 로드되지 않았습니다. 먼저 CreateModel을 실행하세요.")
            return
        
        # 단어 목록이 없으면 모델에서 상위 1000개 단어 선택
        if word_list is None:
            word_list = self.model.wv.index_to_key[:1000]
        
        # 모델에 존재하는 단어만 필터링
        word_list = [word for word in word_list if word in self.model.wv]
        word_vectors = np.array([self.model.wv[word] for word in word_list])

        # PCA로 2차원 축소
        pca = PCA(n_components=2)
        reduced_vectors = pca.fit_transform(word_vectors)
        
        # 한글 폰트 설정 (OS에 맞게 자동 적용)
        import platform
        if platform.system() == "Windows":
            plt.rcParams['font.family'] = 'Malgun Gothic'
        else:
            plt.rcParams['font.family'] = 'Nanum Gothic'
        
        # 색상 설정
        colors = plt.cm.viridis(np.linspace(0, 1, len(word_list)))

        # 시각화
        plt.figure(figsize=(20, 15))
        plt.scatter(reduced_vectors[:, 0], reduced_vectors[:, 1], c=colors, alpha=0.7, edgecolors="k")

        for i, word in enumerate(word_list):
            plt.annotate(word, (reduced_vectors[i, 0] + 0.1, reduced_vectors[i, 1] + 0.1), fontsize=12)

        plt.title("Word2Vec 단어 벡터 시각화 (PCA)", fontsize=16)
        plt.xlabel("PC1", fontsize=14)
        plt.ylabel("PC2", fontsize=14)
        plt.grid(True)
        
        plt.show()