package com.smartdocchat.config;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final RateLimitingFilter rateLimitingFilter;
    private final InternalServiceAuthenticationFilter internalServiceAuthenticationFilter;

    @Value("${cors.allowed-origins:http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000}")
    private String allowedOrigins;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        // CSRF: For a stateless JWT API that uses the Authorization header (not cookies)
        // for authentication, CSRF is not strictly required. However, because CORS is
        // configured with allowCredentials=true (so the browser sends cookies such as
        // the XSRF-TOKEN cookie), we enable CSRF protection with a cookie-based token
        // repository and expose the token via the X-XSRF-TOKEN header. This protects
        // any state-changing browser-initiated requests while remaining compatible
        // with pure Bearer-token API clients (which are unaffected by CSRF).
        CookieCsrfTokenRepository csrfTokenRepository = CookieCsrfTokenRepository.withHttpOnlyFalse();
        csrfTokenRepository.setCookiePath("/");
        csrfTokenRepository.setCookieName("XSRF-TOKEN");
        csrfTokenRepository.setHeaderName("X-XSRF-TOKEN");

        CsrfTokenRequestAttributeHandler csrfRequestHandler = new CsrfTokenRequestAttributeHandler();
        csrfRequestHandler.setCsrfRequestAttributeName(null); // use default token attribute name

        http
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .csrf(csrf -> csrf
                .csrfTokenRepository(csrfTokenRepository)
                .csrfTokenRequestHandler(csrfRequestHandler)
                // Stateless API endpoints that authenticate via Bearer JWT are
                // inherently immune to CSRF; exempt them to avoid breaking non-browser
                // clients. Browser-facing endpoints still require the XSRF-TOKEN.
                .ignoringRequestMatchers(
                    "/auth/**",
                    "/admin/**",
                    "/documents/**",
                    "/chat/**",
                    "/agent/**",
                    "/api/**",
                    "/actuator/**",
                    "/v3/api-docs/**",
                    "/swagger-ui/**",
                    "/swagger-ui.html",
                    "/system/**"
                )
            )
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // Public authentication endpoints
                .requestMatchers("/auth/**").permitAll()
                // Public Swagger/OpenAPI docs
                .requestMatchers(
                    "/v3/api-docs/**",
                    "/swagger-ui/**",
                    "/swagger-ui.html"
                ).permitAll()
                // Only non-sensitive health endpoints are public.
                .requestMatchers("/actuator/health/**", "/actuator/info", "/system/health").permitAll()
                .requestMatchers("/actuator/prometheus").hasRole("SERVICE")
                .requestMatchers("/documents/*/etl-complete", "/documents/*/etl-fail").hasRole("SERVICE")

                // ========== RBAC: Role-based access ==========
                // Admin only: user management and audit logs
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/audit/**").hasRole("ADMIN")

                // Engineer+Admin: data sources and ingestion
                .requestMatchers("/api/datasources/**").hasAnyRole("ENGINEER", "ADMIN")
                .requestMatchers("/api/ingestion/**").hasAnyRole("ENGINEER", "ADMIN")

                // Engineer+Admin: 8D cases and evaluation
                .requestMatchers("/api/8d-cases/**").hasAnyRole("ENGINEER", "ADMIN")
                .requestMatchers("/api/evaluations/**").hasAnyRole("ENGINEER", "ADMIN")

                // Authenticated users: documents and chat
                .requestMatchers(HttpMethod.GET, "/documents/**").authenticated()
                .requestMatchers(HttpMethod.DELETE, "/documents/**").hasAnyRole("ENGINEER", "ADMIN")
                .requestMatchers(HttpMethod.PATCH, "/documents/**").hasAnyRole("ENGINEER", "ADMIN")

                // All other backend APIs require authentication
                .anyRequest().authenticated()
            );

        http.addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        http.addFilterBefore(internalServiceAuthenticationFilter, JwtAuthenticationFilter.class);
        http.addFilterBefore(rateLimitingFilter, InternalServiceAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(Arrays.stream(allowedOrigins.split(",")).map(String::trim).toList());
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"));
        configuration.setAllowedHeaders(Arrays.asList("Authorization", "Content-Type", "Cache-Control", "X-XSRF-TOKEN"));
        configuration.setExposedHeaders(Arrays.asList("Authorization", "X-Request-Id", "X-XSRF-TOKEN"));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}