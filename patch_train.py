import re

with open("ml/forecasting/train_forecasting_models.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add mlflow imports
code = code.replace("import joblib", "import joblib\nimport mlflow\nimport mlflow.sklearn")

# 2. Add df.reset_index(drop=True) in load_feature_store
code = code.replace("        return df", "        df = df.reset_index(drop=True)\n\n        return df")

# 3. Replace chronological_split
old_split = """    def chronological_split(
        self,
        X,
        y
    ):"""

new_split = """    def chronological_split_per_region(
        self,
        X,
        y,
        original_df
    ):"""

code = code.replace(old_split, new_split)

old_split_body = """        total_rows = len(X)

        train_end = int(
            total_rows
            * self.config.train_size
        )

        val_end = int(
            total_rows
            * (
                self.config.train_size
                +
                self.config.validation_size
            )
        )

        # Train
        X_train = (
            X.iloc[:train_end]
        )

        y_train = (
            y.iloc[:train_end]
        )

        # Validation
        X_val = (
            X.iloc[
                train_end:val_end
            ]
        )

        y_val = (
            y.iloc[
                train_end:val_end
            ]
        )

        # Test
        X_test = (
            X.iloc[val_end:]
        )

        y_test = (
            y.iloc[val_end:]
        )"""

new_split_body = """        train_idx, val_idx, test_idx = [], [], []
        
        for region in original_df["region"].unique():
            reg_indices = original_df[original_df["region"] == region].index.values
            total_rows = len(reg_indices)
            train_end = int(total_rows * self.config.train_size)
            val_end = int(total_rows * (self.config.train_size + self.config.validation_size))
            
            train_idx.extend(reg_indices[:train_end])
            val_idx.extend(reg_indices[train_end:val_end])
            test_idx.extend(reg_indices[val_end:])
            
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]"""

code = code.replace(old_split_body, new_split_body)


# 4. Modify run pipeline in __main__
main_start = """    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = (
        pipeline
        .chronological_split(
            X,
            y
        )
    )"""

new_main_start = """    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = (
        pipeline
        .chronological_split_per_region(
            X,
            y,
            df
        )
    )"""
code = code.replace(main_start, new_main_start)


# 5. MLflow rewrite inside evaluate/train
# We'll replace the calls from main to do the mlflow run per model
main_run = """    models = (
        pipeline
        .train_models(
            X_train,
            y_train
        )
    )

    results_df = (
        pipeline
        .evaluate_models(
            models,
            X_val,
            y_val
        )
    )

    pipeline.save_models(
        models
    )

    pipeline.save_report(
        results_df
    )

    (
        best_model_name,
        best_model,
        predictions
    ) = (
        pipeline
        .evaluate_best_model(
            models,
            results_df,
            X_test,
            y_test
        )
    )

    pipeline.generate_feature_importance(
        best_model,
        X_train,
        best_model_name
    )

    pipeline.visualize_predictions(
        y_test,
        predictions
    )

    pipeline.save_best_model(
        best_model,
        best_model_name
    )"""

new_main_run = """    results_df = pipeline.run_mlflow_pipeline(
        X_train, X_val, X_test,
        y_train, y_val, y_test
    )
    pipeline.save_report(results_df)"""
code = code.replace(main_run, new_main_run)


# Add run_mlflow_pipeline method to the class
import textwrap
mlflow_method = textwrap.dedent('''
    # ========================================================
    # MLFLOW PIPELINE
    # ========================================================
    def run_mlflow_pipeline(self, X_train, X_val, X_test, y_train, y_val, y_test):
        mlflow.set_experiment("cloudpulse_forecasting")
        results = []
        
        # 1. Persistence Baseline
        baseline_preds = X_val["cpu_usage"]
        baseline_rmse = np.sqrt(mean_squared_error(y_val, baseline_preds))
        baseline_mae = mean_absolute_error(y_val, baseline_preds)
        baseline_r2 = r2_score(y_val, baseline_preds)
        
        results.append({
            "model": "persistence_baseline",
            "rmse": baseline_rmse,
            "mae": baseline_mae,
            "r2_score": baseline_r2
        })
        logger.info(f"persistence_baseline | RMSE: {baseline_rmse:.4f} | MAE: {baseline_mae:.4f} | R²: {baseline_r2:.4f}")
        
        models = {
            "linear_regression": LinearRegression(),
            "random_forest": RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
            "xgboost": XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=8, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1),
            "lightgbm": LGBMRegressor(n_estimators=200, learning_rate=0.05, max_depth=8, random_state=42),
            # S5: Ablation study model
            "lightgbm_no_pressure": LGBMRegressor(n_estimators=200, learning_rate=0.05, max_depth=8, random_state=42)
        }
        
        for name, model in models.items():
            with mlflow.start_run(run_name=name):
                logger.info(f"Training {name}...")
                
                # S5 Logic
                if name == "lightgbm_no_pressure":
                    drop_cols = ["resource_pressure_score", "sla_breach_risk"]
                    X_tr = X_train.drop(columns=[c for c in drop_cols if c in X_train.columns])
                    X_v = X_val.drop(columns=[c for c in drop_cols if c in X_val.columns])
                    X_te = X_test.drop(columns=[c for c in drop_cols if c in X_test.columns])
                else:
                    X_tr, X_v, X_te = X_train, X_val, X_test
                
                model.fit(X_tr, y_train)
                preds = model.predict(X_v)
                
                rmse = np.sqrt(mean_squared_error(y_val, preds))
                mae = mean_absolute_error(y_val, preds)
                r2 = r2_score(y_val, preds)
                improvement_pct = ((baseline_rmse - rmse) / baseline_rmse) * 100
                
                results.append({"model": name, "rmse": rmse, "mae": mae, "r2_score": r2})
                logger.info(f"{name} | RMSE: {rmse:.4f} | Improv: {improvement_pct:.1f}%")
                
                if improvement_pct < 5.0:
                    logger.warning(f"Model {name} shows < 5% improvement over naive baseline! ({improvement_pct:.1f}%)")
                
                # MLflow logging
                mlflow.log_param("model_type", name)
                mlflow.log_metric("rmse", rmse)
                mlflow.log_metric("mae", mae)
                mlflow.log_metric("r2_score", r2)
                mlflow.log_metric("improvement_pct", improvement_pct)
                
                if hasattr(model, "feature_importances_"):
                    importance_df = pd.DataFrame({"feature": X_tr.columns, "importance": model.feature_importances_}).sort_values("importance", ascending=False).head(20)
                    importance_path = f"artifacts/models/{name}_feature_importance.csv"
                    importance_df.to_csv(importance_path, index=False)
                    mlflow.log_artifact(importance_path)
                
                mlflow.sklearn.log_model(model, "model")
        
        return pd.DataFrame(results)

    # ''')

code = code.replace("    # ========================================================\n    # TRAIN MODELS", mlflow_method + "\n    # ========================================================\n    # TRAIN MODELS")

with open("ml/forecasting/train_forecasting_models.py", "w", encoding="utf-8") as f:
    f.write(code)
