import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'

const storage = new Map()

vi.mock('./authStorage', () => ({
  getUserToken: () => storage.get('token') || ''
}))

import { authHeadersForMedia, isProtectedUploadUrl, normalizeMediaUrl, withAuthMediaHtml, withAuthMediaUrl } from './mediaUrl'

describe('mediaUrl', () => {
  beforeEach(() => {
    storage.clear()
    storage.set('token', 'jwt-sample')
  })

  afterEach(() => {
    storage.clear()
  })

  it('detects protected learning upload paths', () => {
    expect(isProtectedUploadUrl('/uploads/training/learning/12/video/a.mp4')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/task/instructions/1/attachments/a.pdf')).toBe(true)
    expect(isProtectedUploadUrl('/api/file-preview')).toBe(false)
    expect(isProtectedUploadUrl('/uploads/2026/06/27/a.docx')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/chat/files/2026/06/27/a.pdf')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/ai-score/47/roadshow.mp4')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/assistant/1/6/note.md')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/resource-center/3/a.pdf')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/office/versions/9/v1.pptx')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/course-videos/7/a.mp4')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/course-attachments/7/a.pdf')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/course-covers/7/a.png')).toBe(true)
    expect(isProtectedUploadUrl('/uploads/ppt-templates/demo.pdf')).toBe(true)
  })

  it('appends ?t= for protected media', () => {
    const url = withAuthMediaUrl('/uploads/training/learning/12/video/a.mp4')
    expect(url).toContain('/uploads/training/learning/12/video/a.mp4')
    expect(url).toContain('t=jwt-sample')
  })

  it('leaves public uploads untouched', () => {
    expect(withAuthMediaUrl('/uploads/banners/home.png')).toBe('/uploads/banners/home.png')
  })

  it('appends ?t= for chat and legacy date uploads', () => {
    expect(withAuthMediaUrl('/uploads/2026/06/27/a.docx')).toContain('t=jwt-sample')
    expect(withAuthMediaUrl('/uploads/chat/images/2026/06/27/a.png')).toContain('t=jwt-sample')
  })

  it('appends ?t= for course videos and attachments', () => {
    expect(withAuthMediaUrl('/uploads/course-videos/7/a.mp4')).toContain('t=jwt-sample')
    expect(withAuthMediaUrl('/uploads/course-attachments/7/a.pdf')).toContain('t=jwt-sample')
    expect(withAuthMediaUrl('/uploads/course-covers/7/a.png')).toContain('t=jwt-sample')
    expect(withAuthMediaUrl('/uploads/ppt-templates/demo.pdf')).toContain('t=jwt-sample')
    expect(withAuthMediaUrl('/api/ppt-template/download/demo.pdf')).toContain('t=jwt-sample')
    expect(withAuthMediaUrl('/uploads/task/instructions/23/images/a.jpg')).toContain('t=jwt-sample')
  })

  it('rewrites instruction images in HTML', () => {
    const html = withAuthMediaHtml('<p><img src="/uploads/task/instructions/23/images/a.jpg" alt="图"></p>')
    expect(html).toContain('/uploads/task/instructions/23/images/a.jpg')
    expect(html).toContain('t=jwt-sample')
  })

  it('normalizes relative paths', () => {
    expect(normalizeMediaUrl('uploads/foo.pdf')).toBe('/uploads/foo.pdf')
  })

  it('returns Authorization for protected uploads and api', () => {
    expect(authHeadersForMedia('/uploads/training/learning/1/document/a.pdf')).toEqual({
      Authorization: 'Bearer jwt-sample'
    })
    expect(authHeadersForMedia('/api/file-preview')).toEqual({
      Authorization: 'Bearer jwt-sample'
    })
    expect(authHeadersForMedia('/uploads/banners/home.png')).toEqual({})
  })
})
