"""cfx in ML pipelines: composable configs and Jupyter-friendly views.

Defines subsystem configs for preprocessing, model, and training.  A
ConfigView aliases the most-tweaked parameters under short names for
interactive use in a notebook without losing the full structured config.

Usage:
    python ml_pipeline.py                        # print default config
    python ml_pipeline.py --model.learning_rate 0.05 --training.epochs 20
"""

from typing import Literal

from cfx import Alias, Config, ConfigView, Field

#############################################################################
# Subsystem configs
#############################################################################


class PreprocessingConfig(Config):
    confid = "preprocessing"

    normalize: bool = Field(
        True, "Normalize features to zero mean / unit variance"
    )
    remove_outliers: bool = Field(
        False, "Drop rows beyond outlier_threshold sigma"
    )
    outlier_threshold: float = Field(
        3.0, "Outlier threshold (sigma)", minval=1.0
    )


class ModelConfig(Config):
    confid = "model"

    name: Literal["random_forest", "xgboost", "linear"] = Field(
        "random_forest",
        "Model family",
    )
    n_estimators: int = Field(100, "Number of estimators", minval=1)
    max_depth: int = Field(10, "Max tree depth", minval=1)
    learning_rate: float = Field(
        0.1, "Learning rate", minval=0.0001, maxval=1.0
    )


class TrainingConfig(Config):
    confid = "training"

    epochs: int = Field(10, "Training epochs", minval=1)
    batch_size: int = Field(32, "Batch size", minval=1)
    validation_split: float = Field(
        0.2, "Validation split", minval=0.0, maxval=1.0
    )


class PipelineConfig(
    Config,
    components=[PreprocessingConfig, ModelConfig, TrainingConfig],
):
    confid = "pipeline"

    name: str = Field("experiment_01", "Experiment name")


#############################################################################
# Jupyter-friendly view
#############################################################################


class ExperimentView(ConfigView):
    """Curated view exposing only the most frequently tuned parameters.

    In a notebook, bind this to a PipelineConfig instance for concise access::

        exp = ExperimentView(cfg)
        exp.learning_rate = 0.05   # writes through to cfg.model.learning_rate
        exp.epochs = 20            # writes through to cfg.training.epochs
    """

    exp_name = Alias(PipelineConfig.name)
    model_name = Alias(PipelineConfig.model.name)
    learning_rate = Alias(PipelineConfig.model.learning_rate)
    epochs = Alias(PipelineConfig.training.epochs)
    batch_size = Alias(PipelineConfig.training.batch_size)
    normalize = Alias(PipelineConfig.preprocessing.normalize)


#############################################################################
# Entry point
#############################################################################

if __name__ == "__main__":
    import argparse

    import yaml

    parser = argparse.ArgumentParser(description="ML pipeline config demo")
    PipelineConfig.add_arguments(parser)
    args = parser.parse_args()
    cfg = PipelineConfig.from_argparse(args)

    exp = ExperimentView(cfg)
    print(f"Experiment : {exp.exp_name}")
    print(f"Model      : {exp.model_name}")
    print(f"LR / Epochs: {exp.learning_rate} / {exp.epochs}")
    print()
    print(yaml.dump(cfg.to_dict(), default_flow_style=False))
