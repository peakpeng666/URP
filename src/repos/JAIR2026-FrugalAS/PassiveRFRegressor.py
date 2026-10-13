from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

class PassiveRFRegressor:
    def __init__(self, model, type, name, encoder, data, labels):
        self.model = model
        self.model_type = type
        self.model_name = name
        self.encoder = encoder
        self.data = data
        self.labels = labels

    def get_model(self):
        return self.model
    
    def get_model_type(self):
        return self.model_type
    
    def get_model_name(self):
        return self.model_name
    
    def get_encoder(self):
        return self.encoder
    
    def get_data(self):
        return self.data
    
    def get_labels(self):
        return self.labels
    
    def print(self):
        print("Model: ", self.model)
        print("Model Name: ", self.model_name)
        print("Data: ", self.data)
        print("Labels: ", self.labels)

    def fit(self, feature_columns, weight = "No_Weight", timeout = None, penalty = None):
        if weight == "Weighted":
            diff = (self.data[self.model_name].replace(timeout, timeout * penalty)[self.model_name[0]] - self.data[self.model_name].replace(timeout, timeout * penalty)[self.model_name[1]]).abs()
            self.model.fit(self.data[feature_columns], self.labels, sample_weight=diff.values)
        else:
            self.model.fit(self.data[feature_columns], self.labels)
    
    def predict(self, X):
        return self.model.predict(X)
    
    def return_label(self, X):
        predictions = self.model.predict(X)

        return np.where(predictions <= 0, 0, 1)

    def return_rmse_score(self, X, y, set_name):
        predictions = self.model.predict(X)
        rmse = np.sqrt(mean_squared_error(y, predictions))

        print(f"RMSE {self.model_name} in {set_name}: {round(rmse, 2)}")
        print(f"Normalized RMSE {self.model_name} in {set_name}: {round(rmse / np.mean(y) * 100, 2)}%")

    def score(self, X, y):
        predictions = self.model.predict(X)

        print("Mean Absolute Error: ", round(mean_squared_error(y, predictions), 2))
        print("R2 Score: ", round(r2_score(y, predictions), 2))