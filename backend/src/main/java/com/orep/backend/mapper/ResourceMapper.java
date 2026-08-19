package com.orep.backend.mapper;

import com.orep.backend.entity.Resource;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface ResourceMapper {

    @Insert("""
            INSERT INTO resource(name, file_size, ext, file_path, uploaded_by, team_id, category)
            VALUES(#{name}, #{fileSize}, #{ext}, #{filePath}, #{uploadedBy}, #{teamId}, #{category})
            """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    void insert(Resource resource);

    @Select("SELECT r.*, u.username AS uploaderName FROM resource r LEFT JOIN users u ON r.uploaded_by = u.id ORDER BY r.created_at DESC")
    List<Resource> findAll();

    @Select("SELECT r.*, u.username AS uploaderName FROM resource r LEFT JOIN users u ON r.uploaded_by = u.id WHERE r.id = #{id}")
    Resource findById(@Param("id") Integer id);

    @Select("""
            SELECT r.*, u.username AS uploaderName
            FROM resource r
            LEFT JOIN users u ON r.uploaded_by = u.id
            WHERE r.team_id = #{teamId}
            ORDER BY COALESCE(r.updated_at, r.created_at) DESC, r.id DESC
            """)
    List<Resource> findByTeamId(@Param("teamId") Long teamId);

    @Select("""
            SELECT r.*, u.username AS uploaderName
            FROM resource r
            LEFT JOIN users u ON r.uploaded_by = u.id
            WHERE r.team_id IS NULL
            ORDER BY COALESCE(r.updated_at, r.created_at) DESC, r.id DESC
            """)
    List<Resource> findPublic();

    @Update("""
            UPDATE resource
            SET category = #{category}, updated_at = CURRENT_TIMESTAMP
            WHERE id = #{id} AND team_id = #{teamId}
            """)
    int moveToCategory(
            @Param("id") Integer id,
            @Param("teamId") Long teamId,
            @Param("category") String category
    );

    @Select("SELECT r.*, u.username AS uploaderName FROM resource r LEFT JOIN users u ON r.uploaded_by = u.id WHERE r.file_path = #{filePath}")
    Resource findByPath(@Param("filePath") String filePath);

    @Delete("DELETE FROM resource WHERE id = #{id}")
    int deleteById(@Param("id") Integer id);

    @Delete("DELETE FROM resource WHERE id = #{id} AND team_id = #{teamId}")
    int deleteByIdAndTeamId(@Param("id") Integer id, @Param("teamId") Long teamId);

    @Delete("DELETE FROM resource WHERE file_path = #{filePath}")
    int deleteByPath(@Param("filePath") String filePath);
}
