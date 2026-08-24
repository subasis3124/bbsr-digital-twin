import traceback
from pipelines.etl.logging import get_etl_logger
from pipelines.etl.provenance import JobContext
from backend.app.database import SessionLocal
from backend.app.models import ETLJobRun

class BaseETLPipeline:
    def __init__(self, source: str, dataset: str):
        self.source = source
        self.dataset = dataset
        self.logger = get_etl_logger(f"ETL.{source}.{dataset}")

    def run(self, **kwargs):
        """
        Main runner orchestration managing standard lifecycle, transaction safety, and job logging.
        """
        self.logger.info(f"Starting ETL job for {self.source} - {self.dataset}...")
        context = JobContext(self.source, self.dataset)
        db = SessionLocal()
        
        try:
            # Lifecycle Step 1: Discover
            self.logger.info("Step 1: Discovering files/sources...")
            self.discover(context, db, **kwargs)
            
            # Lifecycle Step 2: Download
            self.logger.info("Step 2: Downloading data...")
            self.download(context, db, **kwargs)
            
            # Lifecycle Step 3: Validate (raw format, sizes, etc.)
            self.logger.info("Step 3: Validating raw data...")
            if not self.validate(context, db, **kwargs):
                raise ValueError("Data validation failed at download stage.")
            
            # Lifecycle Step 4: Transform (processing parameters, projections, raster math/clipping)
            self.logger.info("Step 4: Transforming data...")
            transformed_data = self.transform(context, db, **kwargs)
            
            # Lifecycle Step 5: Load (database loading/upserting)
            self.logger.info("Step 5: Loading data to database...")
            self.load(context, db, transformed_data, **kwargs)
            
            # Lifecycle Step 6: Verify (final DB query or sanity check)
            self.logger.info("Step 6: Verifying database state...")
            self.verify(context, db, **kwargs)
            
            # End context
            context.end("success")
            self.logger.info(f"ETL job completed successfully in {context.duration:.2f}s. Processed {context.records_processed} rows (Inserted: {context.records_inserted}, Updated: {context.records_updated}, Skipped: {context.records_skipped}, Rejected: {context.records_rejected}).")

        except Exception as e:
            db.rollback()
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            context.end("failed", error_msg[:1000])
            self.logger.error(f"ETL job failed: {e}")
            raise
            
        finally:
            # Lifecycle Step 7: Record Metadata in etl_job_runs table
            try:
                # To prevent errors if the DB session is in bad state, use a clean transaction
                run_db = SessionLocal()
                try:
                    run_record = ETLJobRun(**context.to_dict())
                    run_db.add(run_record)
                    run_db.commit()
                except Exception as meta_err:
                    self.logger.critical(f"Failed to save ETL job metadata to database: {meta_err}")
                finally:
                    run_db.close()
            except Exception as outer_meta_err:
                self.logger.critical(f"Backup meta-logging failed: {outer_meta_err}")

            db.close()
        
        return context.to_dict()

    # Abstract/lifecycle hooks to be overridden in child classes
    def discover(self, context, db, **kwargs):
        raise NotImplementedError()

    def download(self, context, db, **kwargs):
        raise NotImplementedError()

    def validate(self, context, db, **kwargs) -> bool:
        raise NotImplementedError()

    def transform(self, context, db, **kwargs):
        raise NotImplementedError()

    def load(self, context, db, transformed_data, **kwargs):
        raise NotImplementedError()

    def verify(self, context, db, **kwargs):
        raise NotImplementedError()
