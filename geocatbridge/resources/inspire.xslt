<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

	<xsl:output method="xml" version="1.0" encoding="UTF-8" omit-xml-declaration="no" indent="yes"/>
	<xsl:template match="/">
		<gmd:MD_Metadata xsi:schemaLocation="http://www.isotc211.org/2005/gmd http://schemas.opengis.net/iso/19139/20060504/gmd/gmd.xsd" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml" xmlns:xlink="http://www.w3.org/1999/xlink">
			<gmd:fileIdentifier>
				<gco:CharacterString>
					<xsl:value-of select="metadata/Id"/>
				</gco:CharacterString>
			</gmd:fileIdentifier>
			<gmd:language>
				<xsl:variable name="language" select="metadata/Language" />
				<gmd:LanguageCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#LanguageCode" codeListValue="{$language}">
					<xsl:value-of select="$language"/>
				</gmd:LanguageCode>
			</gmd:language>
			<gmd:hierarchyLevel>
				<gmd:MD_ScopeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_ScopeCode" codeListValue="dataset">dataset</gmd:MD_ScopeCode>
			</gmd:hierarchyLevel>
			<gmd:contact>
				<gmd:CI_ResponsibleParty>
					<gmd:organisationName>
						<gco:CharacterString>
							<xsl:value-of select="metadata/PoC/Name"/>
						</gco:CharacterString>
					</gmd:organisationName>
					<gmd:contactInfo>
						<gmd:CI_Contact>
							<gmd:address>
								<gmd:CI_Address>
									<gmd:electronicMailAddress>
										<gco:CharacterString>
											<xsl:value-of select="metadata/PoC/Mail"/>
										</gco:CharacterString>
									</gmd:electronicMailAddress>
								</gmd:CI_Address>
							</gmd:address>
						</gmd:CI_Contact>
					</gmd:contactInfo>
					<gmd:role>
						<xsl:variable name="role" select="metadata/Organisation/Role" />
						<gmd:CI_RoleCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_RoleCode" codeListValue="{$role}">
							<xsl:value-of select="$role"/>
						</gmd:CI_RoleCode>
					</gmd:role>
				</gmd:CI_ResponsibleParty>
			</gmd:contact>
			<gmd:dateStamp>
				<gco:Date>
					<xsl:value-of select="metadata/Date"/>
				</gco:Date>
			</gmd:dateStamp>
			<gmd:metadataStandardName>
				<gco:CharacterString>ISO19115</gco:CharacterString>
			</gmd:metadataStandardName>
			<gmd:metadataStandardVersion>
				<gco:CharacterString>2003/Cor.1:2006</gco:CharacterString>
			</gmd:metadataStandardVersion>
			<gmd:identificationInfo>
				<gmd:MD_DataIdentification>
					<gmd:citation>
						<gmd:CI_Citation>
							<gmd:title>
								<gco:CharacterString>
									<xsl:value-of select="metadata/Identification/ResourceTitle"/>
								</gco:CharacterString>
							</gmd:title>
							<xsl:if test="metadata/Temporal/CreationDate">
								<gmd:date>
									<gmd:CI_Date>
										<gmd:date>
											<gco:DateTime>
												<xsl:value-of select="metadata/Temporal/CreationDate"/>
											</gco:DateTime>
										</gmd:date>
										<gmd:dateType>
											<gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="creation">creation</gmd:CI_DateTypeCode>
										</gmd:dateType>
									</gmd:CI_Date>
								</gmd:date>
							</xsl:if>
							<xsl:if test="metadata/Temporal/PublicationDate">
								<gmd:date>
									<gmd:CI_Date>
										<gmd:date>
											<gco:DateTime>
												<xsl:value-of select="metadata/Temporal/PublicationDate"/>
											</gco:DateTime>
										</gmd:date>
										<gmd:dateType>
											<gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="publication">publication</gmd:CI_DateTypeCode>
										</gmd:dateType>
									</gmd:CI_Date>
								</gmd:date>
							</xsl:if>
							<xsl:if test="metadata/Temporal/RevisionDate">
								<gmd:date>
									<gmd:CI_Date>
										<gmd:date>
											<gco:DateTime>
												<xsl:value-of select="metadata/Temporal/RevisionDate"/>
											</gco:DateTime>
										</gmd:date>
										<gmd:dateType>
											<gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="revision">revision</gmd:CI_DateTypeCode>
										</gmd:dateType>
									</gmd:CI_Date>
								</gmd:date>
							</xsl:if>
							<gmd:identifier>
								<gmd:RS_Identifier>
									<gmd:code>
										<gco:CharacterString>
											<xsl:value-of select="metadata/Identification/URN/Code"/>
										</gco:CharacterString>
									</gmd:code>
									<gmd:codeSpace>
										<gco:CharacterString>
											<xsl:value-of select="metadata/Identification/URN/CodeSpace"/>
										</gco:CharacterString>
									</gmd:codeSpace>
								</gmd:RS_Identifier>
							</gmd:identifier>
						</gmd:CI_Citation>
					</gmd:citation>
					<gmd:abstract>
						<gco:CharacterString>
							<xsl:value-of select="metadata/Identification/ResourceAbstract"/>
						</gco:CharacterString>
					</gmd:abstract>
					<gmd:pointOfContact>
						<gmd:CI_ResponsibleParty>
							<gmd:organisationName>
								<gco:CharacterString>
									<xsl:value-of select="metadata/Organisation/Name"/>
								</gco:CharacterString>
							</gmd:organisationName>
							<gmd:contactInfo>
								<gmd:CI_Contact>
									<gmd:address>
										<gmd:CI_Address>
											<gmd:electronicMailAddress>
												<gco:CharacterString>
													<xsl:value-of select="metadata/Organisation/Mail"/>
												</gco:CharacterString>
											</gmd:electronicMailAddress>
										</gmd:CI_Address>
									</gmd:address>
								</gmd:CI_Contact>
							</gmd:contactInfo>
							<gmd:role>
								<gmd:CI_RoleCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_RoleCode" codeListValue="owner">
									<xsl:value-of select="metadata/Organisation/Role"/>
								</gmd:CI_RoleCode>
							</gmd:role>
						</gmd:CI_ResponsibleParty>
					</gmd:pointOfContact>
					<gmd:descriptiveKeywords>
						<gmd:MD_Keywords>
							<gmd:keyword>
								<gco:CharacterString>
									<xsl:value-of select="metadata/Keyword"/>
								</gco:CharacterString>
							</gmd:keyword>
							<gmd:thesaurusName>
								<gmd:CI_Citation>
									<gmd:title>
										<gco:CharacterString>GEMET - INSPIRE themes, version 1.0</gco:CharacterString>
									</gmd:title>
									<gmd:date>
										<gmd:CI_Date>
											<gmd:date>
												<gco:Date>2008-06-01</gco:Date>
											</gmd:date>
											<gmd:dateType>
												<gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="publication">publication</gmd:CI_DateTypeCode>
											</gmd:dateType>
										</gmd:CI_Date>
									</gmd:date>
								</gmd:CI_Citation>
							</gmd:thesaurusName>
						</gmd:MD_Keywords>
					</gmd:descriptiveKeywords>
					<gmd:resourceConstraints>
						<gmd:MD_Constraints>
							<gmd:useLimitation>
								<gco:CharacterString>
									<xsl:value-of select="metadata/Constraints/Use"/>
								</gco:CharacterString>
							</gmd:useLimitation>
						</gmd:MD_Constraints>
					</gmd:resourceConstraints>
					<gmd:resourceConstraints>
						<gmd:MD_LegalConstraints>
							<gmd:accessConstraints>
								<gmd:MD_RestrictionCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_RestrictionCode" codeListValue="otherRestrictions">otherRestrictions</gmd:MD_RestrictionCode>
							</gmd:accessConstraints>
							<gmd:otherConstraints>
								<gco:CharacterString>
									<xsl:value-of select="metadata/Constraints/Access"/>
								</gco:CharacterString>
							</gmd:otherConstraints>
						</gmd:MD_LegalConstraints>
					</gmd:resourceConstraints>
					<gmd:language>
						<gmd:LanguageCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#LanguageCode" codeListValue="por">por</gmd:LanguageCode>
					</gmd:language>
					<gmd:topicCategory>
						<gmd:MD_TopicCategoryCode>
							<xsl:value-of select="metadata/Classification/TopicCategory"/>
						</gmd:MD_TopicCategoryCode>
					</gmd:topicCategory>
					<gmd:extent>
						<gmd:EX_Extent>
							<gmd:geographicElement>
								<gmd:EX_GeographicBoundingBox>
									<gmd:westBoundLongitude>
										<gco:Decimal>
											<xsl:value-of select="metadata/Geographic/West"/>
										</gco:Decimal>
									</gmd:westBoundLongitude>
									<gmd:eastBoundLongitude>
										<gco:Decimal>
											<xsl:value-of select="metadata/Geographic/East"/>
										</gco:Decimal>
									</gmd:eastBoundLongitude>
									<gmd:southBoundLatitude>
										<gco:Decimal>
											<xsl:value-of select="metadata/Geographic/South"/>
										</gco:Decimal>
									</gmd:southBoundLatitude>
									<gmd:northBoundLatitude>
										<gco:Decimal>
											<xsl:value-of select="metadata/Geographic/North"/>
										</gco:Decimal>
									</gmd:northBoundLatitude>
								</gmd:EX_GeographicBoundingBox>
							</gmd:geographicElement>
						</gmd:EX_Extent>
					</gmd:extent>
					<gmd:extent>
						<gmd:EX_Extent>
							<gmd:temporalElement>
								<gmd:EX_TemporalExtent>
									<gmd:extent>
										<gml:TimePeriod gml:id="ID1fcbd696-8c4f-4b18-9609-b53e4e62cab7" xsi:type="gml:TimePeriodType">
											<gml:beginPosition>
												<xsl:value-of select="normalize-space(metadata/Temporal/Begin)"/>
											</gml:beginPosition>
											<gml:endPosition>
												<xsl:value-of select="normalize-space(metadata/Temporal/End)"/>
											</gml:endPosition>
										</gml:TimePeriod>
									</gmd:extent>
								</gmd:EX_TemporalExtent>
							</gmd:temporalElement>
						</gmd:EX_Extent>
					</gmd:extent>
				</gmd:MD_DataIdentification>
			</gmd:identificationInfo>
			<gmd:distributionInfo>
				<gmd:MD_Distribution>
					<gmd:distributionFormat>
						<gmd:MD_Format>
							<gmd:name gco:nilReason="inapplicable" />
							<gmd:version gco:nilReason="inapplicable" />
						</gmd:MD_Format>
					</gmd:distributionFormat>
					<gmd:transferOptions>
						<gmd:MD_DigitalTransferOptions />
					</gmd:transferOptions>
				</gmd:MD_Distribution>
			</gmd:distributionInfo>
			<gmd:dataQualityInfo>
				<gmd:DQ_DataQuality>
					<gmd:scope>
						<gmd:DQ_Scope>
							<gmd:level>
								<gmd:MD_ScopeCode codeListValue="dataset" codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/ML_gmxCodelists.xml#MD_ScopeCode">dataset</gmd:MD_ScopeCode>
							</gmd:level>
						</gmd:DQ_Scope>
					</gmd:scope>
					<gmd:report>
						<gmd:DQ_DomainConsistency>
							<gmd:result>
								<gmd:DQ_ConformanceResult>
									<gmd:specification>
										<gmd:CI_Citation>
											<gmd:title>
												<gco:CharacterString>Commission Regulation (EU) No 1089/2010 of 23 November 2010 implementing Directive 2007/2/EC of the European Parliament and of the Council as regards interoperability of spatial data sets and services</gco:CharacterString>
											</gmd:title>
											<gmd:date>
												<gmd:CI_Date>
													<gmd:date>
														<gco:Date>2010-12-08</gco:Date>
													</gmd:date>
													<gmd:dateType>
														<gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/codelist/ML_gmxCodelists.xml#CI_DateTypeCode" codeListValue="publication">publication</gmd:CI_DateTypeCode>
													</gmd:dateType>
												</gmd:CI_Date>
											</gmd:date>
										</gmd:CI_Citation>
									</gmd:specification>
									<gmd:explanation>
										<gco:CharacterString>See the referenced specification</gco:CharacterString>
									</gmd:explanation>
									<gmd:pass>
										<gco:Boolean>true</gco:Boolean>
									</gmd:pass>
								</gmd:DQ_ConformanceResult>
							</gmd:result>
						</gmd:DQ_DomainConsistency>
					</gmd:report>
					<gmd:lineage>
						<gmd:LI_Lineage>
							<gmd:statement>
								<gco:CharacterString>
									<xsl:value-of select="metadata/Quality/Lineage"/>
								</gco:CharacterString>
							</gmd:statement>
						</gmd:LI_Lineage>
					</gmd:lineage>
				</gmd:DQ_DataQuality>
			</gmd:dataQualityInfo>
		</gmd:MD_Metadata>

	</xsl:template>    

</xsl:stylesheet>
