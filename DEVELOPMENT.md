# Development Guide

## Project Structure Overview

```
Smart Document Chatbot/
├── backend/              # Spring Boot Backend
│   ├── src/
│   │   ├── main/java/com/smartdocchat/
│   │   │   ├── config/          # Spring configuration
│   │   │   ├── controller/      # REST endpoints
│   │   │   ├── service/         # Business logic
│   │   │   ├── entity/          # JPA entities
│   │   │   ├── repository/      # Data access layer
│   │   │   ├── dto/             # Data transfer objects
│   │   │   ├── exception/       # Exception handling
│   │   │   └── util/            # Utilities
│   │   └── resources/
│   │       └── application.yml  # Configuration
│   └── pom.xml
├── frontend/             # React Frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── App.jsx       # Main app
│   │   └── index.css     # Styles
│   ├── package.json
│   └── tailwind.config.js
├── docker/               # Docker configs
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── README.md             # Overview
├── SETUP.md              # Setup instructions
├── API.md                # API documentation
├── DEPLOYMENT.md         # Deployment guide
└── .gitignore
```

---

## Backend Development

### Adding a New Endpoint

1. **Create DTO** (if needed)
   ```java
   // src/main/java/com/smartdocchat/dto/MyRequest.java
   @Data
   @NoArgsConstructor
   @AllArgsConstructor
   @Builder
   public class MyRequest {
       private String field1;
       private Integer field2;
   }
   ```

2. **Create Controller**
   ```java
   @RestController
   @RequestMapping("/my-resource")
   @RequiredArgsConstructor
   public class MyController {
       private final MyService myService;

       @PostMapping
       public ResponseEntity<MyResponse> create(@RequestBody MyRequest request) {
           return ResponseEntity.ok(myService.create(request));
       }
   }
   ```

3. **Create Service**
   ```java
   @Service
   @RequiredArgsConstructor
   @Slf4j
   public class MyService {
       private final MyRepository repository;

       public MyResponse create(MyRequest request) {
           // Business logic
           return new MyResponse();
       }
   }
   ```

4. **Create Repository** (if needed)
   ```java
   @Repository
   public interface MyRepository extends JpaRepository<MyEntity, Long> {
       List<MyEntity> findByStatus(String status);
   }
   ```

### Database Migrations

1. **Using Hibernate** (auto with `ddl-auto: update`)
   - Changes are detected automatically
   - Good for dev, use Flyway for production

2. **Manual Migration** (Future)
   ```sql
   ALTER TABLE documents ADD COLUMN new_field VARCHAR(255);
   ```

### Testing

```bash
# Run all tests
mvn test

# Run specific test
mvn test -Dtest=DocumentServiceTest

# With coverage
mvn test jacoco:report
```

---

## Frontend Development

### Adding a New Component

1. **Create Component**
   ```jsx
   // src/components/MyComponent.jsx
   import React from 'react';

   function MyComponent({ prop1, prop2, onAction }) {
     return (
       <div className="p-4 bg-white rounded-lg">
         <h2 className="text-lg font-semibold">{prop1}</h2>
         <button
           onClick={() => onAction(prop2)}
           className="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
         >
           Action
         </button>
       </div>
     );
   }

   export default MyComponent;
   ```

2. **Use in App**
   ```jsx
   import MyComponent from './components/MyComponent';

   function App() {
     return (
       <div>
         <MyComponent 
           prop1="Title" 
           prop2="value"
           onAction={(val) => console.log(val)}
         />
       </div>
     );
   }
   ```

### Styling with Tailwind

```jsx
// Responsive
<div className="p-4 md:p-8 lg:p-12">
  Responsive padding
</div>

// Dark mode (when enabled)
<div className="bg-white dark:bg-gray-900">
  Auto theme
</div>

// Custom utilities
<div className="group hover:shadow-xl transition">
  Group hover effect
</div>
```

### Debugging

1. **React DevTools**
   - Install browser extension
   - Inspect components
   - Check state/props

2. **Network Tab**
   - Monitor API calls
   - Check request/response
   - Verify headers

3. **Console**
   ```javascript
   // Add debug logs
   console.log('Debug:', variable);
   console.error('Error:', error);
   ```

---

## Integration with OpenAI & Qdrant

### OpenAI Integration (TODO)

```java
@Service
public class EmbeddingService {
    private final OpenAIConfig config;

    public String[] generateEmbedding(String text) {
        // Call OpenAI API
        // return embeddings
    }

    public String generateResponse(String prompt) {
        // Call OpenAI ChatCompletion API
        // return response
    }
}
```

### Qdrant Integration (TODO)

```java
@Service
public class VectorStorageService {
    private final QdrantClient client;

    public void storeVector(String documentId, double[] embedding, String text) {
        // Store in Qdrant
    }

    public List<String> search(double[] queryEmbedding, int topK) {
        // Semantic search
        // return results
    }
}
```

---

## Performance Tips

### Backend
- Use connection pooling (HikariCP)
- Cache frequently accessed data
- Batch database operations
- Use indexes on large tables
- Implement pagination

### Frontend
- Code splitting with React.lazy
- Memoize expensive computations
- Virtualize long lists
- Lazy load images
- Minimize bundle size

### Database
```sql
-- Add indexes
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM documents WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## Common Tasks

### Debug Mode

**Backend**
```bash
# Set log level to DEBUG
export LOGGING_LEVEL_COM_SMARTDOCCHAT=DEBUG
mvn spring-boot:run
```

**Frontend**
```bash
# React DevTools + console
npm start
```

### Reset Database

```bash
# Option 1: Docker
docker-compose down -v
docker-compose up

# Option 2: Manual SQL
psql -h localhost -U postgres -d smart_doc_chatbot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Clear Cache

```bash
# Frontend
# localStorage.clear() in browser console

# Backend
# Restart application
```

### Generate Seed Data

```java
@Component
public class DataSeeder implements CommandLineRunner {
    @Override
    public void run(String... args) {
        // Create dummy data for testing
    }
}
```

---

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "feat: add my feature"

# Push
git push origin feature/my-feature

# Create PR on GitHub
# After review, merge to main

# Clean up
git branch -d feature/my-feature
```

---

## Environment Variables

Create `.env.local` in project root:

```env
# Backend
OPENAI_API_KEY=sk-...
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/smart_doc_chatbot
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=postgres
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Frontend
REACT_APP_API_URL=http://localhost:8080/api
```

---

## IDE Setup

### VS Code
1. Install extensions:
   - Spring Boot Extension Pack
   - REST Client
   - Thunder Client

2. Create `.vscode/launch.json`:
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Spring Boot",
         "type": "java",
         "name": "Spring Boot App",
         "request": "launch",
         "cwd": "${workspaceFolder}/backend",
         "mainClass": "com.smartdocchat.SmartDocChatbotApplication",
         "args": ""
       }
     ]
   }
   ```

### IntelliJ IDEA
1. Open project root
2. Configure Maven SDK
3. Mark `src` folders
4. Run with Ctrl+Shift+F10

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | `lsof -ti:8080 \| xargs kill -9` |
| Database connection failed | Check PostgreSQL is running: `docker ps` |
| No such file or directory | Use forward slashes: `backend/src` not `backend\src` |
| Module not found | Run `mvn install` or `npm install` |
| Tailwind not working | Run `npm run build:css` or use CDN in `index.html` |

---

## Resources

- [Spring Boot Docs](https://spring.io/projects/spring-boot)
- [React Docs](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [OpenAI API](https://platform.openai.com/docs)
- [Qdrant Docs](https://qdrant.tech/documentation/)

---

Happy coding! 🚀
