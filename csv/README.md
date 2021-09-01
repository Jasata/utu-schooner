# Storage for CSV files

During development, this directory will contain testing CSV files, but eventually, this location should be the upload directory for Web UI -based enrollment.

Yes, uploads CAN be handled without writing the POST'ed file on disk, but we WANT to store it for possible inspection afterwards.

Uploaded files shall be prefixed with the same datetime stamp which will be recorded in the enrollee -table (meaning that one current datetime will be taken at the beginning of processing and applied in the INSERTs and as a filename prefix).

