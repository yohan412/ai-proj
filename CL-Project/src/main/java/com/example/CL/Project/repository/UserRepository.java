package com.example.CL.Project.repository;

import com.example.CL.Project.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    /**
     * Finds a user by their username.
     * Spring Data JPA automatically implements this method based on its name.
     *
     * @param username the username to search for
     * @return an Optional containing the user if found, or an empty Optional otherwise
     */
    Optional<User> findByUsername(String username);
}
