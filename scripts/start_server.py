"""Start the API server for testing."""
import uvicorn

if __name__ == "__main__":
    print("Starting ATS Resume API on http://localhost:8000")
    print("Docs available at http://localhost:8000/docs")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

